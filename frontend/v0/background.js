// ABOUTME: Chrome extension background service worker for Lockin focus tracker.
// ABOUTME: Sends browsing events to backend, polls for nudges, handles session lifecycle.

const API_BASE = "http://localhost:8000";

// --- Tab tracking: send events to backend on every page load ---

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url && !tab.url.startsWith("chrome://")) {
        chrome.storage.local.get(['activeTask'], (result) => {
            if (result.activeTask) {
                chrome.scripting.executeScript({
                    target: { tabId: tabId },
                    files: ["content.js"]
                }, (injectionResults) => {
                    if (injectionResults && injectionResults[0].result) {
                        const pageData = injectionResults[0].result;
                        const payload = {
                            action: "SAVE_CONTEXT",
                            task: result.activeTask,
                            pageInfo: pageData
                        };
                        console.log("Sending context:", payload);
                        sendToBackend(payload);
                    }
                });
            }
        });
    }
});

function sendToBackend(payload) {
    fetch(`${API_BASE}/webhook/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            console.log("Event saved:", data);
            // Store session_id from first response
            if (data.session_id) {
                chrome.storage.local.set({ sessionId: data.session_id });
            }
        })
        .catch(error => console.error("Error sending context:", error));
}

// --- Nudge polling via chrome.alarms (survives service worker sleep) ---

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === "nudgeCheck") {
        checkNudge();
    }
});

function checkNudge() {
    chrome.storage.local.get(['sessionId', 'activeTask'], (result) => {
        if (!result.sessionId || !result.activeTask) return;

        fetch(`${API_BASE}/api/sessions/${result.sessionId}/nudge`)
            .then(response => response.json())
            .then(data => {
                if (data.nudge) {
                    chrome.notifications.create(`nudge-${Date.now()}`, {
                        type: "basic",
                        iconUrl: "icon48.png",
                        title: "LockIn — Stay Focused!",
                        message: data.message,
                        buttons: [{ title: "Go Back" }],
                        priority: 2
                    });
                    // Store return_to URL for the notification button
                    if (data.return_to) {
                        chrome.storage.local.set({ returnTo: data.return_to });
                    }
                }
            })
            .catch(error => console.error("Nudge check failed:", error));
    });
}

// Handle "Go Back" button click on nudge notification
chrome.notifications.onButtonClicked.addListener((notificationId, buttonIndex) => {
    if (notificationId.startsWith("nudge-") && buttonIndex === 0) {
        chrome.storage.local.get(['returnTo'], (result) => {
            if (result.returnTo) {
                chrome.tabs.update({ url: result.returnTo });
            }
        });
    }
});

// --- Session lifecycle: start/stop nudge polling ---

// Listen for messages from popup.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "START_SESSION") {
        // Start nudge polling (every 1 minute)
        chrome.alarms.create("nudgeCheck", { periodInMinutes: 1 });
        console.log("Nudge polling started");
        sendResponse({ ok: true });
    }

    if (message.type === "END_SESSION") {
        // Stop nudge polling
        chrome.alarms.clear("nudgeCheck");

        chrome.storage.local.get(['sessionId'], (result) => {
            if (!result.sessionId) {
                sendResponse({ ok: false, error: "No session" });
                return;
            }

            // End session on backend
            fetch(`${API_BASE}/api/sessions/${result.sessionId}/end`, { method: "POST" })
                .then(r => r.json())
                .then(() => {
                    // Fetch report and open in new tab
                    const reportUrl = `${API_BASE}/api/sessions/${result.sessionId}/report`;
                    chrome.tabs.create({ url: reportUrl });

                    // Clear stored state
                    chrome.storage.local.remove(['sessionId', 'activeTask', 'returnTo']);
                    console.log("Session ended, report opened");
                    sendResponse({ ok: true });
                })
                .catch(error => {
                    console.error("End session failed:", error);
                    sendResponse({ ok: false, error: error.message });
                });
        });

        return true; // Keep message channel open for async sendResponse
    }
});

// ABOUTME: Chrome extension background service worker for Lockin focus tracker.
// ABOUTME: Handles event ingestion, nudge polling, session lifecycle, and Q&A queries.

const API_BASE = "http://localhost:8000";

// --- WORKFLOW A: BACKGROUND TRACKING ---
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url
        && !tab.url.startsWith("chrome://")
        && !tab.url.startsWith("chrome-extension://")
        && !tab.url.startsWith("chrome.google.com")) {

        chrome.storage.local.get(['activeTask'], (result) => {
            if (result.activeTask) {
                chrome.scripting.executeScript({
                    target: { tabId: tabId },
                    files: ["content.js"]
                }, (injectionResults) => {
                    if (chrome.runtime.lastError) {
                        console.log("Skip (restricted page):", chrome.runtime.lastError.message);
                        return;
                    }
                    if (injectionResults && injectionResults[0].result) {
                        const payload = {
                            action: "SAVE_CONTEXT",
                            task: result.activeTask,
                            pageInfo: injectionResults[0].result
                        };
                        console.log("Sending context:", payload.pageInfo.url);
                        saveContext(payload);
                    }
                });
            }
        });
    }
});

async function saveContext(payload) {
    try {
        const response = await fetch(`${API_BASE}/webhook/save`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            console.error("Save failed:", response.status, await response.text());
            return;
        }

        const data = await response.json();
        console.log("Event saved:", data.domain, "session:", data.session_id);

        // Store session_id from first response
        if (data.session_id) {
            chrome.storage.local.set({ sessionId: data.session_id });
        }

        // Notify popup
        chrome.runtime.sendMessage({
            type: "INGEST_SUCCESS",
            data: `Saved: ${data.domain} (${data.classification})`
        }).catch(() => {}); // popup may be closed

    } catch (error) {
        console.error("Save error:", error);
    }
}

// --- WORKFLOW B: Q&A via RocketRide Agent + Neo4j ---
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "ASK_AGENT") {
        chrome.storage.local.get(['sessionId'], async (result) => {
            try {
                const response = await fetch(`${API_BASE}/api/query`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        query: request.query,
                        session_id: result.sessionId || null
                    })
                });
                const data = await response.json();
                chrome.runtime.sendMessage({
                    type: "AGENT_ANSWER",
                    answer: data.answer || "No answer received."
                }).catch(() => {});
            } catch (error) {
                chrome.runtime.sendMessage({
                    type: "ERROR",
                    error: error.toString()
                }).catch(() => {});
            }
        });
    }

    if (request.type === "START_SESSION") {
        chrome.alarms.create("nudgeCheck", { periodInMinutes: 1 });
        console.log("Session started, nudge polling active");
        sendResponse({ ok: true });
    }

    if (request.type === "END_SESSION") {
        chrome.alarms.clear("nudgeCheck");

        chrome.storage.local.get(['sessionId'], async (result) => {
            if (!result.sessionId) {
                console.log("No session to end");
                sendResponse({ ok: false, error: "No session yet — browse some pages first" });
                return;
            }

            try {
                const endResp = await fetch(`${API_BASE}/api/sessions/${result.sessionId}/end`, { method: "POST" });
                if (!endResp.ok) {
                    const detail = await endResp.text();
                    console.error("End session failed:", detail);
                    sendResponse({ ok: false, error: detail });
                    return;
                }

                // Open report in new tab
                chrome.tabs.create({ url: `${API_BASE}/api/sessions/${result.sessionId}/report` });

                // Clear state
                chrome.storage.local.remove(['sessionId', 'activeTask', 'returnTo']);
                console.log("Session ended, report opened");
                sendResponse({ ok: true });

            } catch (error) {
                console.error("End session error:", error);
                sendResponse({ ok: false, error: error.message });
            }
        });

        return true; // async sendResponse
    }
});

// --- NUDGE POLLING VIA CHROME ALARMS ---
chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === "nudgeCheck") {
        checkNudge();
    }
});

function checkNudge() {
    chrome.storage.local.get(['sessionId', 'activeTask'], async (result) => {
        if (!result.sessionId || !result.activeTask) return;

        try {
            const response = await fetch(`${API_BASE}/api/sessions/${result.sessionId}/nudge`);
            if (!response.ok) {
                console.error("Nudge check failed:", response.status);
                return;
            }

            const data = await response.json();
            if (data.nudge) {
                // Show structured nudge overlay on the active tab
                chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                    if (tabs[0] && !tabs[0].url.startsWith("chrome://")) {
                        chrome.tabs.sendMessage(tabs[0].id, {
                            action: 'SHOW_NUDGE',
                            domain: data.current_domain,
                            minutes: Math.max(1, Math.ceil((data.off_task_seconds || 0) / 60)),
                            task: data.task,
                            returnTo: data.return_to
                        }).catch(() => {});
                    }
                });

                if (data.return_to) {
                    chrome.storage.local.set({ returnTo: data.return_to });
                }
            }
        } catch (error) {
            console.error("Nudge error:", error);
        }
    });
}

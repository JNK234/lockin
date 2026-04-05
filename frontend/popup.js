// ABOUTME: Popup UI logic for the LockIn Chrome extension.
// ABOUTME: Two-state UI (idle/tracking), timer, session lifecycle.

document.addEventListener('DOMContentLoaded', () => {
    const idleView = document.getElementById('idleView');
    const trackingView = document.getElementById('trackingView');
    const taskInput = document.getElementById('taskInput');
    const startBtn = document.getElementById('startBtn');
    const endBtn = document.getElementById('endBtn');
    const closeBtn = document.getElementById('closeBtn');
    const taskDisplay = document.getElementById('taskDisplay');
    const timerDisplay = document.getElementById('timerDisplay');
    const insightsLink = document.getElementById('insightsLink');
    const settingsBtn = document.getElementById('settingsBtn');

    let timerInterval = null;

    // Load current state and show correct view
    chrome.storage.local.get(['activeTask', 'sessionStartTime'], (result) => {
        if (result.activeTask) {
            showTrackingView(result.activeTask, result.sessionStartTime);
        } else {
            showIdleView();
        }
    });

    function showIdleView() {
        idleView.classList.remove('hidden');
        trackingView.classList.add('hidden');
        if (timerInterval) clearInterval(timerInterval);
    }

    function showTrackingView(task, startTime) {
        idleView.classList.add('hidden');
        trackingView.classList.remove('hidden');
        taskDisplay.textContent = task;
        startTimer(startTime);
    }

    function startTimer(startTime) {
        if (timerInterval) clearInterval(timerInterval);
        const start = startTime ? new Date(startTime).getTime() : Date.now();

        function updateTimer() {
            const elapsed = Math.floor((Date.now() - start) / 1000);
            const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const secs = String(elapsed % 60).padStart(2, '0');
            timerDisplay.textContent = `${mins}:${secs}`;
        }

        updateTimer();
        timerInterval = setInterval(updateTimer, 1000);
    }

    // Start Task
    startBtn.addEventListener('click', () => {
        const task = taskInput.value.trim();
        if (!task) return;

        const startTime = new Date().toISOString();
        chrome.storage.local.set({ activeTask: task, sessionStartTime: startTime }, () => {
            chrome.runtime.sendMessage({ type: "START_SESSION" });
            showTrackingView(task, startTime);
        });
    });

    // End Session
    endBtn.addEventListener('click', () => {
        endBtn.textContent = 'Ending...';
        endBtn.disabled = true;

        chrome.runtime.sendMessage({ type: "END_SESSION" }, (response) => {
            endBtn.textContent = 'END SESSION';
            endBtn.disabled = false;

            if (response && response.ok) {
                taskInput.value = '';
                chrome.storage.local.remove(['sessionStartTime']);
                showIdleView();
            } else {
                endBtn.textContent = response?.error || 'Error — try again';
                setTimeout(() => { endBtn.textContent = 'END SESSION'; }, 3000);
            }
        });
    });

    // Close popup
    closeBtn.addEventListener('click', () => window.close());

    // Settings
    settingsBtn.addEventListener('click', () => chrome.runtime.openOptionsPage());

    // View insights — open report for last session
    insightsLink.addEventListener('click', () => {
        chrome.storage.local.get(['sessionId', 'lastCompletedSessionId'], (result) => {
            const id = result.sessionId || result.lastCompletedSessionId;
            if (id) {
                getApiBase().then((base) => {
                    chrome.tabs.create({ url: `${base}/report/${id}` });
                });
            }
        });
    });
});

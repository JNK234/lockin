// ABOUTME: Options page logic for saving and loading LockIn settings.
// ABOUTME: Validates input, persists to chrome.storage, and recreates alarms on change.

document.addEventListener('DOMContentLoaded', () => {
    const apiBaseInput = document.getElementById('apiBase');
    const nudgeIntervalInput = document.getElementById('nudgeInterval');
    const saveBtn = document.getElementById('saveBtn');
    const toast = document.getElementById('toast');
    const urlError = document.getElementById('urlError');

    // Load current values
    chrome.storage.local.get(['apiBaseUrl', 'nudgeIntervalMinutes'], (result) => {
        apiBaseInput.value = result.apiBaseUrl || DEFAULT_API_BASE;
        nudgeIntervalInput.value = result.nudgeIntervalMinutes || DEFAULT_NUDGE_INTERVAL;
    });

    saveBtn.addEventListener('click', () => {
        const rawUrl = apiBaseInput.value.trim();
        const interval = parseInt(nudgeIntervalInput.value) || DEFAULT_NUDGE_INTERVAL;

        // Validate URL
        if (rawUrl && !rawUrl.match(/^https?:\/\//)) {
            urlError.style.display = 'block';
            return;
        }
        urlError.style.display = 'none';

        // Normalize
        const apiBase = rawUrl.replace(/\/+$/, '') || DEFAULT_API_BASE;
        const clampedInterval = Math.max(1, Math.min(30, interval));

        apiBaseInput.value = apiBase;
        nudgeIntervalInput.value = clampedInterval;

        chrome.storage.local.set({
            apiBaseUrl: apiBase,
            nudgeIntervalMinutes: clampedInterval,
        }, () => {
            // Recreate alarm if session is active
            chrome.storage.local.get(['activeTask'], (result) => {
                if (result.activeTask) {
                    chrome.alarms.clear("nudgeCheck", () => {
                        chrome.alarms.create("nudgeCheck", { periodInMinutes: clampedInterval });
                    });
                }
            });

            // Show toast
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        });
    });
});

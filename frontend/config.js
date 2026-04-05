// ABOUTME: Shared configuration resolver for the LockIn Chrome extension.
// ABOUTME: Provides getApiBase() and getNudgeInterval() used by background, popup, and options.

const DEFAULT_API_BASE = "http://localhost:8000";
const DEFAULT_NUDGE_INTERVAL = 1;

function getApiBase() {
    return new Promise((resolve) => {
        chrome.storage.local.get(['apiBaseUrl'], (result) => {
            let url = result.apiBaseUrl || DEFAULT_API_BASE;
            url = url.replace(/\/+$/, '');
            resolve(url);
        });
    });
}

function getNudgeInterval() {
    return new Promise((resolve) => {
        chrome.storage.local.get(['nudgeIntervalMinutes'], (result) => {
            const val = parseInt(result.nudgeIntervalMinutes) || DEFAULT_NUDGE_INTERVAL;
            resolve(Math.max(1, Math.min(30, val)));
        });
    });
}

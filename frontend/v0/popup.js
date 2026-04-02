// ABOUTME: Popup UI logic for the Lockin Chrome extension.
// ABOUTME: Manages task input, start/stop session, communicates with background worker.

document.addEventListener('DOMContentLoaded', () => {
    const taskInput = document.getElementById('taskInput');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusDiv = document.getElementById('status');

    // Load current state
    chrome.storage.local.get(['activeTask'], (result) => {
        if (result.activeTask) {
            taskInput.value = result.activeTask;
            statusDiv.innerText = `Status: Tracking "${result.activeTask}"`;
            statusDiv.style.color = "green";
        }
    });

    startBtn.addEventListener('click', () => {
        const task = taskInput.value.trim();
        if (task) {
            chrome.storage.local.set({ activeTask: task }, () => {
                statusDiv.innerText = `Status: Tracking "${task}"`;
                statusDiv.style.color = "green";
                // Tell background to start nudge polling
                chrome.runtime.sendMessage({ type: "START_SESSION" });
            });
        }
    });

    stopBtn.addEventListener('click', () => {
        statusDiv.innerText = "Status: Ending session...";
        statusDiv.style.color = "orange";

        // Tell background to end session + open report
        chrome.runtime.sendMessage({ type: "END_SESSION" }, (response) => {
            taskInput.value = '';
            statusDiv.innerText = "Status: Idle";
            statusDiv.style.color = "gray";
        });
    });
});

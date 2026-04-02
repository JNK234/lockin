// ABOUTME: Popup UI logic for the Lockin Chrome extension.
// ABOUTME: Manages task tracking, session lifecycle, and Q&A interface.

document.addEventListener('DOMContentLoaded', () => {
    const taskInput = document.getElementById('taskInput');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusDiv = document.getElementById('status');
    const ingestResponseDiv = document.getElementById('ingestResponse');
    const questionInput = document.getElementById('questionInput');
    const askBtn = document.getElementById('askBtn');
    const agentResponseDiv = document.getElementById('agentResponse');

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
                chrome.runtime.sendMessage({ type: "START_SESSION" });
            });
        }
    });

    stopBtn.addEventListener('click', () => {
        statusDiv.innerText = "Status: Ending session...";
        statusDiv.style.color = "orange";

        chrome.runtime.sendMessage({ type: "END_SESSION" }, (response) => {
            if (response && response.ok) {
                taskInput.value = '';
                statusDiv.innerText = "Status: Session ended — report opened";
                statusDiv.style.color = "gray";
                ingestResponseDiv.innerText = '';
            } else {
                const err = response?.error || "Unknown error";
                statusDiv.innerText = `Status: ${err}`;
                statusDiv.style.color = "red";
            }
        });
    });

    askBtn.addEventListener('click', () => {
        const question = questionInput.value.trim();
        if (question) {
            agentResponseDiv.style.display = 'block';
            agentResponseDiv.innerText = "Agent is thinking...";
            chrome.runtime.sendMessage({ action: "ASK_AGENT", query: question });
        }
    });

    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.type === "INGEST_SUCCESS") {
            ingestResponseDiv.innerText = message.data;
            setTimeout(() => { ingestResponseDiv.innerText = ''; }, 4000);
        }
        else if (message.type === "AGENT_ANSWER") {
            agentResponseDiv.style.display = 'block';
            agentResponseDiv.innerText = message.answer;
        }
        else if (message.type === "ERROR") {
            agentResponseDiv.style.display = 'block';
            agentResponseDiv.innerText = `Error: ${message.error}`;
        }
    });
});

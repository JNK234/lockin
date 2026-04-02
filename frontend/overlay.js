// ABOUTME: Content script that shows an overlay on the page for nudges and AI responses.
// ABOUTME: Injected on all pages via manifest content_scripts.

function showAgentResponseOnPage(aiText, returnTo) {
    const existingOverlay = document.getElementById('rocketride-ai-overlay');
    if (existingOverlay) { existingOverlay.remove(); }

    const overlay = document.createElement('div');
    overlay.id = 'rocketride-ai-overlay';
    Object.assign(overlay.style, {
        position: 'fixed', bottom: '20px', right: '20px', width: '350px',
        backgroundColor: '#ffffff', border: '1px solid #e0e0e0', borderRadius: '8px',
        boxShadow: '0 10px 25px rgba(0,0,0,0.2)', zIndex: '999999',
        fontFamily: 'sans-serif', overflow: 'hidden', display: 'flex', flexDirection: 'column'
    });

    const header = document.createElement('div');
    Object.assign(header.style, {
        backgroundColor: '#6c5ce7', color: 'white', padding: '10px 15px',
        fontWeight: 'bold', fontSize: '14px', display: 'flex',
        justifyContent: 'space-between', alignItems: 'center'
    });
    header.innerText = 'Lockin — Stay Focused!';

    const closeBtn = document.createElement('button');
    closeBtn.innerText = '✕';
    Object.assign(closeBtn.style, {
        background: 'none', border: 'none', color: 'white',
        cursor: 'pointer', fontSize: '16px'
    });
    closeBtn.onclick = () => overlay.remove();
    header.appendChild(closeBtn);

    const content = document.createElement('div');
    Object.assign(content.style, {
        padding: '15px', fontSize: '14px', color: '#333',
        lineHeight: '1.5', maxHeight: '400px', overflowY: 'auto'
    });
    content.innerHTML = aiText.replace(/\n/g, '<br>');

    overlay.appendChild(header);
    overlay.appendChild(content);

    // Add "Go Back" button if return_to URL is provided
    if (returnTo) {
        const goBackBtn = document.createElement('button');
        goBackBtn.innerText = 'Go Back to Task';
        Object.assign(goBackBtn.style, {
            margin: '0 15px 15px', padding: '10px', backgroundColor: '#28a745',
            color: 'white', border: 'none', borderRadius: '4px',
            cursor: 'pointer', fontWeight: 'bold', fontSize: '14px'
        });
        goBackBtn.onclick = () => {
            window.location.href = returnTo;
        };
        overlay.appendChild(goBackBtn);
    }

    document.body.appendChild(overlay);
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'SHOW_AI_OVERLAY') {
        showAgentResponseOnPage(message.text, message.returnTo);
    }
});

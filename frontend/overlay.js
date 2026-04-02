// ABOUTME: Content script that shows an overlay on the page for nudges and AI responses.
// ABOUTME: Injected on all pages via manifest content_scripts.

function showAgentResponseOnPage(aiText, returnTo) {
    const existingOverlay = document.getElementById('lockin-overlay');
    if (existingOverlay) { existingOverlay.remove(); }

    const overlay = document.createElement('div');
    overlay.id = 'lockin-overlay';
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
    header.innerText = 'LockIn — Stay Focused!';

    const closeBtn = document.createElement('button');
    closeBtn.innerText = '✕';
    Object.assign(closeBtn.style, {
        background: 'none', border: 'none', color: 'white',
        cursor: 'pointer', fontSize: '16px'
    });
    closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        document.getElementById('lockin-overlay')?.remove();
    });
    header.appendChild(closeBtn);

    const content = document.createElement('div');
    Object.assign(content.style, {
        padding: '15px', fontSize: '14px', color: '#333',
        lineHeight: '1.5', maxHeight: '400px', overflowY: 'auto'
    });
    content.innerHTML = aiText.replace(/\n/g, '<br>');

    overlay.appendChild(header);
    overlay.appendChild(content);

    // Add action button
    const actionBtn = document.createElement('button');
    if (returnTo) {
        actionBtn.innerText = 'Go Back to Task';
        actionBtn.style.backgroundColor = '#28a745';
        actionBtn.onclick = () => { window.location.href = returnTo; };
    } else {
        actionBtn.innerText = 'Got it, refocusing!';
        actionBtn.style.backgroundColor = '#007bff';
        actionBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            document.getElementById('lockin-overlay')?.remove();
        });
    }
    Object.assign(actionBtn.style, {
        margin: '0 15px 15px', padding: '10px',
        color: 'white', border: 'none', borderRadius: '4px',
        cursor: 'pointer', fontWeight: 'bold', fontSize: '14px'
    });
    overlay.appendChild(actionBtn);

    document.body.appendChild(overlay);
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'SHOW_AI_OVERLAY') {
        showAgentResponseOnPage(message.text, message.returnTo);
    }
});

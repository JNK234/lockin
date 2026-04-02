// ABOUTME: Content script that shows nudge overlays on web pages.
// ABOUTME: Light theme with orange accent for off-task warnings.

function showNudge(data) {
    const existing = document.getElementById('lockin-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'lockin-overlay';
    Object.assign(overlay.style, {
        position: 'fixed', bottom: '20px', right: '20px', width: '380px',
        backgroundColor: '#FFFFFF', borderRadius: '12px',
        boxShadow: '0 12px 40px rgba(0,0,0,0.15)', zIndex: '2147483647',
        fontFamily: "'Inter', -apple-system, sans-serif",
        overflow: 'hidden', border: '1px solid #E5E7EB'
    });

    // Header: ⚠ OFF-TASK
    const header = document.createElement('div');
    Object.assign(header.style, {
        background: '#FEF3C7', padding: '12px 16px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
    });

    const headerLeft = document.createElement('div');
    Object.assign(headerLeft.style, {
        display: 'flex', alignItems: 'center', gap: '8px',
        fontWeight: '700', fontSize: '13px', color: '#D97706',
        textTransform: 'uppercase', letterSpacing: '0.5px'
    });
    headerLeft.textContent = '\u26A0 OFF-TASK';

    const closeBtn = document.createElement('button');
    closeBtn.textContent = '\u2715';
    Object.assign(closeBtn.style, {
        background: 'none', border: 'none', color: '#D97706',
        cursor: 'pointer', fontSize: '16px', padding: '0', width: 'auto'
    });
    closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        document.getElementById('lockin-overlay')?.remove();
    });

    header.appendChild(headerLeft);
    header.appendChild(closeBtn);

    // Body
    const body = document.createElement('div');
    Object.assign(body.style, { padding: '16px', lineHeight: '1.5' });

    const message = document.createElement('div');
    Object.assign(message.style, { fontSize: '14px', color: '#1A1A2E', marginBottom: '6px' });
    const domain = data.domain || 'this site';
    const minutes = data.minutes || '?';
    message.innerHTML = `You've been on <strong style="color:#D97706">${domain}</strong> for ${minutes} minute${minutes !== 1 ? 's' : ''}`;

    const taskLine = document.createElement('div');
    Object.assign(taskLine.style, { fontSize: '13px', color: '#6B7280', marginBottom: '16px' });
    taskLine.textContent = `Get back to: ${data.task || 'your task'}`;

    body.appendChild(message);
    body.appendChild(taskLine);

    // Buttons row
    const btnRow = document.createElement('div');
    Object.assign(btnRow.style, { display: 'flex', gap: '8px' });

    const goBackBtn = document.createElement('button');
    goBackBtn.textContent = '\u2190 Go Back';
    Object.assign(goBackBtn.style, {
        flex: '1', padding: '10px', borderRadius: '8px', border: 'none',
        fontFamily: 'inherit', fontSize: '13px', fontWeight: '600',
        cursor: 'pointer', color: '#FFFFFF',
        background: data.returnTo ? '#E8A838' : '#9CA3AF'
    });
    goBackBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (data.returnTo) {
            window.location.href = data.returnTo;
        } else {
            document.getElementById('lockin-overlay')?.remove();
        }
    });

    const dismissBtn = document.createElement('button');
    dismissBtn.textContent = 'Dismiss';
    Object.assign(dismissBtn.style, {
        flex: '1', padding: '10px', borderRadius: '8px', border: 'none',
        fontFamily: 'inherit', fontSize: '13px', fontWeight: '600',
        cursor: 'pointer', background: '#F3F4F6', color: '#6B7280'
    });
    dismissBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        document.getElementById('lockin-overlay')?.remove();
    });

    btnRow.appendChild(goBackBtn);
    btnRow.appendChild(dismissBtn);
    body.appendChild(btnRow);

    overlay.appendChild(header);
    overlay.appendChild(body);
    document.body.appendChild(overlay);
}

// Legacy support for text-based messages
function showAgentResponseOnPage(aiText, returnTo) {
    showNudge({ domain: '', minutes: '', task: '', returnTo: returnTo, rawText: aiText });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'SHOW_NUDGE') {
        showNudge(message);
    }
    if (message.action === 'SHOW_AI_OVERLAY') {
        showAgentResponseOnPage(message.text, message.returnTo);
    }
});

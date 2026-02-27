/**
 * Protocol Pulse — AI Chat Widget
 * Embeddable chat bubble with RAG-powered answers.
 */
(function() {
    'use strict';

    var history = [];
    var isOpen = false;
    var isLoading = false;

    function createWidget() {
        // Chat bubble trigger
        var bubble = document.createElement('button');
        bubble.id = 'ppChatBubble';
        bubble.className = 'pp-chat-bubble';
        bubble.setAttribute('aria-label', 'Ask Alex — AI Analyst');
        bubble.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/><path d="M7 9h2v2H7zm4 0h2v2h-2zm4 0h2v2h-2z"/></svg>';
        bubble.onclick = toggleChat;
        document.body.appendChild(bubble);

        // Chat panel
        var panel = document.createElement('div');
        panel.id = 'ppChatPanel';
        panel.className = 'pp-chat-panel';
        panel.innerHTML = `
            <div class="pp-chat-panel__header">
                <div class="pp-chat-panel__header-left">
                    <div class="pp-chat-panel__avatar">
                        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>
                    </div>
                    <div>
                        <div class="pp-chat-panel__name">Alex</div>
                        <div class="pp-chat-panel__status"><span class="pp-chat-panel__dot"></span>Protocol Pulse AI</div>
                    </div>
                </div>
                <button class="pp-chat-panel__close" onclick="window.ppToggleChat()" aria-label="Close chat">&times;</button>
            </div>
            <div class="pp-chat-panel__messages" id="ppChatMessages">
                <div class="pp-chat-msg pp-chat-msg--assistant">
                    <div class="pp-chat-msg__content">
                        Hey, I'm Alex — your Protocol Pulse AI analyst. Ask me anything about Bitcoin, crypto markets, or topics from our Intel Briefs.
                    </div>
                </div>
            </div>
            <div class="pp-chat-panel__input-wrap">
                <input type="text"
                       class="pp-chat-panel__input"
                       id="ppChatInput"
                       placeholder="Ask about Bitcoin..."
                       autocomplete="off"
                       maxlength="500">
                <button class="pp-chat-panel__send" id="ppChatSend" onclick="window.ppSendChat()" aria-label="Send">
                    <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                </button>
            </div>
        `;
        document.body.appendChild(panel);

        // Input handler
        var input = document.getElementById('ppChatInput');
        if (input) {
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    window.ppSendChat();
                }
            });
        }
    }

    function toggleChat() {
        var panel = document.getElementById('ppChatPanel');
        var bubble = document.getElementById('ppChatBubble');
        if (!panel) return;

        isOpen = !isOpen;
        panel.classList.toggle('pp-chat-panel--open', isOpen);
        bubble.classList.toggle('pp-chat-bubble--active', isOpen);

        if (isOpen) {
            var input = document.getElementById('ppChatInput');
            if (input) setTimeout(function() { input.focus(); }, 200);
        }
    }
    window.ppToggleChat = toggleChat;

    function sendChat() {
        if (isLoading) return;
        var input = document.getElementById('ppChatInput');
        var query = (input.value || '').trim();
        if (!query) return;

        input.value = '';
        appendMessage('user', query);
        history.push({ role: 'user', content: query });

        isLoading = true;
        showTyping();

        fetch('/api/chat/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, history: history.slice(-6) })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            removeTyping();
            isLoading = false;

            var answer = data.answer || 'Sorry, I couldn\'t process that question.';
            appendMessage('assistant', answer, data.sources);
            history.push({ role: 'assistant', content: answer });
        })
        .catch(function(err) {
            removeTyping();
            isLoading = false;
            appendMessage('assistant', 'Connection error. Please try again.');
        });
    }
    window.ppSendChat = sendChat;

    function appendMessage(role, content, sources) {
        var container = document.getElementById('ppChatMessages');
        if (!container) return;

        var msg = document.createElement('div');
        msg.className = 'pp-chat-msg pp-chat-msg--' + role;

        // Render markdown-like formatting
        var html = renderMarkdown(content);

        // Add source links
        if (sources && sources.length > 0) {
            html += '<div class="pp-chat-sources">';
            html += '<span class="pp-chat-sources__label">Sources:</span>';
            sources.forEach(function(s) {
                html += '<a href="' + s.url + '" class="pp-chat-sources__link" target="_blank">' + escapeHtml(s.title) + '</a>';
            });
            html += '</div>';
        }

        msg.innerHTML = '<div class="pp-chat-msg__content">' + html + '</div>';
        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
    }

    function showTyping() {
        var container = document.getElementById('ppChatMessages');
        if (!container) return;
        var typing = document.createElement('div');
        typing.className = 'pp-chat-msg pp-chat-msg--assistant pp-chat-typing';
        typing.innerHTML = '<div class="pp-chat-msg__content"><span class="pp-chat-dots"><span></span><span></span><span></span></span></div>';
        container.appendChild(typing);
        container.scrollTop = container.scrollHeight;
    }

    function removeTyping() {
        var el = document.querySelector('.pp-chat-typing');
        if (el) el.remove();
    }

    function renderMarkdown(text) {
        if (!text) return '';
        // Basic markdown: bold, italic, links, code, lists
        var html = escapeHtml(text);
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        html = html.replace(/`(.+?)`/g, '<code>$1</code>');
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color:var(--pp-teal);">$1</a>');
        html = html.replace(/\n- /g, '\n&bull; ');
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    function escapeHtml(s) {
        if (!s) return '';
        var d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    // Inject styles
    var style = document.createElement('style');
    style.textContent = `
        .pp-chat-bubble {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 56px;
            height: 56px;
            background: var(--pp-teal, #00d4aa);
            border: none;
            border-radius: 50%;
            color: #0a0a0a;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 20px rgba(0, 212, 170, 0.3);
            z-index: 1500;
            transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
        }
        .pp-chat-bubble:hover {
            transform: scale(1.08);
            box-shadow: 0 6px 28px rgba(0, 212, 170, 0.45);
        }
        .pp-chat-bubble--active { opacity: 0; pointer-events: none; transform: scale(0.8); }

        .pp-chat-panel {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 400px;
            max-width: calc(100vw - 32px);
            height: 560px;
            max-height: calc(100vh - 100px);
            background: var(--pp-surface, #111111);
            border: 1px solid var(--pp-border, rgba(255,255,255,0.08));
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
            z-index: 1600;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            opacity: 0;
            transform: translateY(20px) scale(0.95);
            pointer-events: none;
            transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
        }
        .pp-chat-panel--open {
            opacity: 1;
            transform: translateY(0) scale(1);
            pointer-events: auto;
        }

        .pp-chat-panel__header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            border-bottom: 1px solid var(--pp-border, rgba(255,255,255,0.08));
            background: var(--pp-surface-2, #1a1a1a);
        }
        .pp-chat-panel__header-left { display: flex; align-items: center; gap: 12px; }
        .pp-chat-panel__avatar {
            width: 36px; height: 36px;
            background: rgba(0, 212, 170, 0.15);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--pp-teal, #00d4aa);
        }
        .pp-chat-panel__name {
            font-weight: 600;
            font-size: 0.9375rem;
            color: var(--pp-text, #f0f0f0);
        }
        .pp-chat-panel__status {
            font-size: 0.6875rem;
            color: var(--pp-text-muted, rgba(255,255,255,0.4));
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .pp-chat-panel__dot {
            width: 6px; height: 6px;
            background: var(--pp-green, #00e676);
            border-radius: 50%;
            display: inline-block;
        }
        .pp-chat-panel__close {
            background: none;
            border: none;
            color: var(--pp-text-muted, rgba(255,255,255,0.4));
            font-size: 1.5rem;
            cursor: pointer;
            padding: 4px 8px;
            line-height: 1;
        }
        .pp-chat-panel__close:hover { color: var(--pp-text, #f0f0f0); }

        .pp-chat-panel__messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .pp-chat-msg { display: flex; }
        .pp-chat-msg--user { justify-content: flex-end; }
        .pp-chat-msg--assistant { justify-content: flex-start; }

        .pp-chat-msg__content {
            max-width: 85%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 0.875rem;
            line-height: 1.5;
            word-wrap: break-word;
        }
        .pp-chat-msg--user .pp-chat-msg__content {
            background: var(--pp-teal, #00d4aa);
            color: #0a0a0a;
            border-bottom-right-radius: 4px;
        }
        .pp-chat-msg--assistant .pp-chat-msg__content {
            background: var(--pp-surface-2, #1a1a1a);
            color: var(--pp-text, #f0f0f0);
            border: 1px solid var(--pp-border, rgba(255,255,255,0.08));
            border-bottom-left-radius: 4px;
        }
        .pp-chat-msg__content code {
            background: rgba(0,0,0,0.3);
            padding: 1px 5px;
            border-radius: 3px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8125rem;
        }
        .pp-chat-msg__content a { color: var(--pp-teal, #00d4aa); text-decoration: underline; }
        .pp-chat-msg--user .pp-chat-msg__content a { color: #0a0a0a; }

        .pp-chat-sources {
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid var(--pp-border, rgba(255,255,255,0.08));
        }
        .pp-chat-sources__label {
            font-size: 0.6875rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--pp-text-muted, rgba(255,255,255,0.4));
            display: block;
            margin-bottom: 4px;
        }
        .pp-chat-sources__link {
            display: block;
            font-size: 0.75rem;
            color: var(--pp-teal, #00d4aa) !important;
            text-decoration: none !important;
            padding: 2px 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .pp-chat-sources__link:hover { text-decoration: underline !important; }

        .pp-chat-dots { display: flex; gap: 4px; padding: 4px 0; }
        .pp-chat-dots span {
            width: 7px; height: 7px;
            background: var(--pp-text-muted, rgba(255,255,255,0.4));
            border-radius: 50%;
            animation: pp-dot-bounce 1.4s ease-in-out infinite both;
        }
        .pp-chat-dots span:nth-child(2) { animation-delay: 0.16s; }
        .pp-chat-dots span:nth-child(3) { animation-delay: 0.32s; }
        @keyframes pp-dot-bounce {
            0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
            40% { transform: scale(1); opacity: 1; }
        }

        .pp-chat-panel__input-wrap {
            display: flex;
            gap: 8px;
            padding: 12px 16px;
            border-top: 1px solid var(--pp-border, rgba(255,255,255,0.08));
            background: var(--pp-surface-2, #1a1a1a);
        }
        .pp-chat-panel__input {
            flex: 1;
            background: var(--pp-surface, #111111);
            border: 1px solid var(--pp-border, rgba(255,255,255,0.08));
            border-radius: 8px;
            padding: 10px 14px;
            color: var(--pp-text, #f0f0f0);
            font-family: 'Inter', sans-serif;
            font-size: 0.875rem;
            outline: none;
            transition: border-color 0.2s ease;
        }
        .pp-chat-panel__input:focus {
            border-color: var(--pp-teal, #00d4aa);
        }
        .pp-chat-panel__input::placeholder {
            color: var(--pp-text-muted, rgba(255,255,255,0.4));
        }
        .pp-chat-panel__send {
            background: var(--pp-teal, #00d4aa);
            border: none;
            border-radius: 8px;
            color: #0a0a0a;
            cursor: pointer;
            width: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: opacity 0.15s ease;
        }
        .pp-chat-panel__send:hover { opacity: 0.85; }

        @media (max-width: 480px) {
            .pp-chat-panel {
                bottom: 0;
                right: 0;
                width: 100vw;
                max-width: 100vw;
                height: calc(100vh - 64px);
                max-height: calc(100vh - 64px);
                border-radius: 16px 16px 0 0;
            }
            .pp-chat-bubble { bottom: 16px; right: 16px; }
        }
    `;
    document.head.appendChild(style);

    // Init on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createWidget);
    } else {
        createWidget();
    }
})();

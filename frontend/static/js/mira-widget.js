/**
 * Mira Chat Widget — global script (loaded on every page via base.html)
 *
 * On search.html, the search-app.js Mira section takes precedence
 * (it checks for window._miraWidgetLoaded). On all other pages,
 * this script handles the FAB, chat, greeting and messaging.
 */
(function() {
    'use strict';

    // Don't double-init if search-app.js already wired Mira
    if (window._miraWidgetActive) return;

    const widget = document.getElementById('mira-widget');
    if (!widget) return;  // no widget HTML on this page (e.g. login)

    window._miraWidgetActive = true;

    const miraState = {
        isOpen: false,
        hasGreeted: false,
        usesDu: null,
        history: [],
        idleTimer: null,
    };

    // ── Core open/close ─────────────────────────────────────────
    function openMiraChat() {
        miraState.isOpen = true;
        widget.classList.add('open');
        widget.classList.remove('mira-idle');
        resetIdleTimer();
        if (!miraState.hasGreeted) {
            loadGreeting();
            miraState.hasGreeted = true;
        }
        const inp = document.getElementById('mira-input');
        if (inp) setTimeout(() => inp.focus(), 300);
    }

    function closeMiraChat() {
        miraState.isOpen = false;
        widget.classList.remove('open', 'mira-idle');
        clearTimeout(miraState.idleTimer);
        sessionStorage.setItem('mira-closed', '1');
    }

    function toggleMiraChat() {
        if (miraState.isOpen) closeMiraChat(); else openFromFab();
    }

    function openFromFab() {
        sessionStorage.removeItem('mira-closed');
        widget.style.display = '';
        openMiraChat();
    }

    // ── Idle transparency ───────────────────────────────────────
    function resetIdleTimer() {
        widget.classList.remove('mira-idle');
        clearTimeout(miraState.idleTimer);
        if (!miraState.isOpen) return;
        miraState.idleTimer = setTimeout(() => {
            if (miraState.isOpen) widget.classList.add('mira-idle');
        }, 5000);
    }

    // Click outside = close
    document.addEventListener('mousedown', function(e) {
        if (miraState.isOpen && !widget.contains(e.target)) closeMiraChat();
    });

    // Reset idle on interaction
    ['mouseenter', 'mousemove', 'click', 'keydown'].forEach(evt => {
        widget.addEventListener(evt, resetIdleTimer);
    });

    // ── Messages ────────────────────────────────────────────────
    function addMessage(content, isUser) {
        const container = document.getElementById('mira-messages');
        if (!container) return;
        const msg = document.createElement('div');
        msg.className = 'mira-message ' + (isUser ? 'user' : 'mira');
        msg.textContent = content;
        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
    }

    function showTyping() {
        const container = document.getElementById('mira-messages');
        if (!container) return;
        const typing = document.createElement('div');
        typing.className = 'mira-typing'; typing.id = 'mira-typing';
        typing.innerHTML = '<span></span><span></span><span></span>';
        container.appendChild(typing);
        container.scrollTop = container.scrollHeight;
    }

    function hideTyping() {
        const el = document.getElementById('mira-typing'); if (el) el.remove();
    }

    function loadGreeting() {
        fetch('/api/mira/greeting')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data && data.greeting) addMessage(data.greeting, false);
                else addMessage('Hi! I\'m Mira — ask me anything about your job search.', false);
            })
            .catch(() => addMessage('Hi! I\'m Mira — ask me anything about your job search.', false));
    }

    async function sendMessage() {
        const input = document.getElementById('mira-input');
        if (!input) return;
        const text = input.value.trim();
        if (!text) return;
        addMessage(text, true);
        input.value = ''; input.style.height = 'auto';

        // Detect Du/Sie
        if (miraState.usesDu === null) {
            if (/\b(du|dein|dich|dir)\b/i.test(text)) miraState.usesDu = true;
            else if (/\b(Sie|Ihr|Ihnen|Ihre)\b/.test(text)) miraState.usesDu = false;
        }

        showTyping();
        miraState.history.push({ role: 'user', content: text });

        try {
            const response = await fetch('/api/mira/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    uses_du: miraState.usesDu,
                    history: miraState.history.slice(0, -1),
                }),
            });
            hideTyping();
            if (response.ok) {
                const data = await response.json();
                addMessage(data.reply, false);
                miraState.history.push({ role: 'assistant', content: data.reply });
                if (miraState.history.length > 20) miraState.history = miraState.history.slice(-20);
            } else {
                addMessage('Sorry, something went wrong. Please try again.', false);
                miraState.history.pop();
            }
        } catch (error) {
            hideTyping();
            addMessage('I seem to be offline right now. Please try again later.', false);
            miraState.history.pop();
        }
    }

    // ── Wire handlers ───────────────────────────────────────────
    function wire() {
        const fabBtn = document.getElementById('mira-fab-btn');
        const minBtn = document.getElementById('mira-minimize-btn');
        const sendBtn = document.getElementById('mira-send-btn');
        const miraInput = document.getElementById('mira-input');

        if (fabBtn) fabBtn.addEventListener('click', function(e) { e.stopPropagation(); toggleMiraChat(); });
        if (minBtn) minBtn.addEventListener('click', function(e) { e.stopPropagation(); closeMiraChat(); });
        if (sendBtn) sendBtn.addEventListener('click', function(e) { e.stopPropagation(); sendMessage(); });
        if (miraInput) {
            miraInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
            });
            miraInput.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = Math.min(this.scrollHeight, 100) + 'px';
            });
            miraInput.addEventListener('focus', resetIdleTimer);
        }
    }

    // Expose for other scripts (e.g. search player bar)
    window.miraWidget = {
        open: openMiraChat,
        close: closeMiraChat,
        toggle: toggleMiraChat,
        addMessage: addMessage,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wire);
    } else {
        wire();
    }
})();

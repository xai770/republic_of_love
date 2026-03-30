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
        screenContext: null,
    };

    // ── Screen context (quick-action pills) ─────────────────────
    function detectLang() {
        try { return document.documentElement.lang || 'de'; } catch(_) { return 'de'; }
    }

    function loadScreenContext() {
        var path = window.location.pathname.replace(/\/$/, '') || '/';
        var lang = detectLang();
        var url = '/api/mira/screen-context?path=' + encodeURIComponent(path) + '&lang=' + encodeURIComponent(lang);
        fetch(url)
            .then(function(r) { return r.ok ? r.json() : null; })
            .then(function(data) {
                if (data && data.found) {
                    miraState.screenContext = data;
                    renderQuickActions(data.quick_actions || []);
                    // Use context greeting if no messages yet
                    if (data.illustration) {
                        updateIllustration(data.illustration);
                    }
                }
            })
            .catch(function() {});
    }

    function renderQuickActions(actions) {
        var container = document.getElementById('mira-quick-actions');
        if (!container) return;
        container.innerHTML = '';
        if (!actions.length) { container.style.display = 'none'; return; }
        container.style.display = '';
        actions.forEach(function(a) {
            var btn = document.createElement('button');
            btn.className = 'mira-pill';
            btn.textContent = a.label;
            btn.addEventListener('click', function() {
                addMessage(a.label, true);
                sendMessageText(a.message);
            });
            container.appendChild(btn);
        });
    }

    function updateIllustration(filename) {
        var img = widget.querySelector('.mira-avatar-img');
        if (img) img.src = '/static/images/Mira/' + filename;
    }

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
        // Use screen context greeting if available
        if (miraState.screenContext && miraState.screenContext.greeting) {
            addMessage(miraState.screenContext.greeting, false);
            return;
        }
        fetch('/api/mira/greeting')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data && data.greeting) addMessage(data.greeting, false);
                else addMessage('Hi! I\'m Mira — ask me anything about your job search.', false);
            })
            .catch(() => addMessage('Hi! I\'m Mira — ask me anything about your job search.', false));
    }

    async function sendMessageText(text) {
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

        await sendMessageText(text);
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
        loadScreenContext: loadScreenContext,
        refreshCreditBadge: refreshCreditBadge,
    };

    function refreshCreditBadge() {
        fetch('/api/account/credit-balance')
            .then(function(r) { return r.ok ? r.json() : null; })
            .then(function(data) {
                if (!data) return;
                var badge = document.getElementById('mira-credit-badge');
                if (badge) {
                    badge.textContent = data.badge;
                    badge.title = '€' + data.balance_eur + ' credit';
                }
            })
            .catch(function() {});
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() { wire(); loadScreenContext(); refreshCreditBadge(); });
    } else {
        wire();
        loadScreenContext();
        refreshCreditBadge();
    }
})();

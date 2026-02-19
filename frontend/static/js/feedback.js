/**
 * Feedback Widget — "Fehler melden" / "Report an issue"
 *
 * Usage: included on every page via base.html.
 * Activated by clicking the lightbulb icon in the header bar.
 *
 * Flow:
 *   1. User clicks 💡 button → overlay appears
 *   2. User can optionally drag to highlight a region
 *   3. User picks a category + writes a description
 *   4. html2canvas captures a screenshot (with annotation box drawn on it)
 *   5. POST /api/feedback → saved to DB
 *   6. "Thank you" confirmation
 */
(function () {
    'use strict';

    /* ── state ── */
    let overlayEl = null;
    let isDrawing = false;
    let startX = 0, startY = 0;
    let rect = { x: 0, y: 0, w: 0, h: 0 };

    /* ── i18n helpers ── */
    const LANG = document.documentElement.lang || 'de';
    const T = {
        de: {
            title: 'Fehler melden',
            category: 'Kategorie',
            bug: 'Fehler / Bug',
            suggestion: 'Verbesserungsvorschlag',
            question: 'Frage',
            other: 'Sonstiges',
            description: 'Beschreibung',
            placeholder: 'Was ist passiert? Was hast du erwartet?',
            highlight_hint: 'Optional: Ziehe einen Rahmen um den Bereich auf dem Bildschirm.',
            submit: 'Absenden',
            cancel: 'Abbrechen',
            sending: 'Wird gesendet…',
            success_title: 'Danke!',
            success_msg: 'Dein Feedback wurde gespeichert. Wir kümmern uns darum.',
            error: 'Fehler beim Senden. Bitte versuche es erneut.',
            close: 'Schließen',
            description_required: 'Bitte beschreibe das Problem.',
        },
        en: {
            title: 'Report an issue',
            category: 'Category',
            bug: 'Bug / Error',
            suggestion: 'Suggestion',
            question: 'Question',
            other: 'Other',
            description: 'Description',
            placeholder: 'What happened? What did you expect?',
            highlight_hint: 'Optional: drag a rectangle to highlight an area on screen.',
            submit: 'Submit',
            cancel: 'Cancel',
            sending: 'Sending…',
            success_title: 'Thank you!',
            success_msg: 'Your feedback has been saved. We\'ll look into it.',
            error: 'Error sending feedback. Please try again.',
            close: 'Close',
            description_required: 'Please describe the issue.',
        }
    };
    function t(key) { return (T[LANG] || T.de)[key] || (T.de)[key] || key; }

    /* ── inject CSS so the widget is self-contained on ANY page ── */
    function injectStyles() {
        if (document.getElementById('fb-injected-css')) return;
        const s = document.createElement('style');
        s.id = 'fb-injected-css';
        s.textContent = `
/* Feedback widget — injected by feedback.js */
#feedback-overlay{display:none;position:fixed;inset:0;z-index:100000}
#feedback-overlay.active{display:block}
.fb-highlight-layer{position:fixed;inset:0;cursor:crosshair;background:rgba(0,0,0,.08);z-index:100001}
.fb-highlight-box{display:none;position:fixed;border:3px dashed #ef4444;border-radius:4px;background:rgba(239,68,68,.08);pointer-events:none;z-index:100005}
.fb-panel{position:fixed;top:0;right:0;width:380px;max-width:90vw;height:100vh;background:rgba(255,255,255,.45);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);box-shadow:-4px 0 24px rgba(0,0,0,.15);z-index:100003;padding:24px;display:flex;flex-direction:column;gap:12px;overflow-y:auto;cursor:crosshair;animation:fbSlideIn .2s ease-out}
@keyframes fbSlideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}
.fb-panel-header{display:flex;justify-content:space-between;align-items:center}
.fb-panel-header h3{margin:0;font-size:1.1rem;color:var(--text-primary,#333)}
.fb-close{background:none;border:none;font-size:1.4rem;cursor:pointer;color:var(--text-secondary,#666);padding:4px 8px;border-radius:4px}
.fb-close:hover{background:rgba(0,0,0,.05)}
.fb-hint{font-size:.82rem;color:var(--text-secondary,#888);margin:0;line-height:1.4}
.fb-label{font-size:.82rem;font-weight:600;color:var(--text-secondary,#555);margin-top:4px}
.fb-select{width:100%;padding:8px 12px;border:1px solid var(--border-color,#ddd);border-radius:8px;background:var(--bg-primary,#f5f5f5);color:var(--text-primary,#333);font-size:.9rem}
.fb-textarea{width:100%;padding:10px 12px;border:1px solid var(--border-color,#ddd);border-radius:8px;background:var(--bg-primary,#f5f5f5);color:var(--text-primary,#333);font-size:.9rem;resize:vertical;font-family:inherit;line-height:1.5}
.fb-textarea:focus,.fb-select:focus{outline:none;border-color:var(--accent,#667eea);box-shadow:0 0 0 3px rgba(102,126,234,.15)}
.fb-actions{display:flex;gap:8px;margin-top:8px}
.fb-btn{flex:1;padding:10px 16px;border:none;border-radius:8px;font-size:.9rem;font-weight:600;cursor:pointer;transition:all .15s}
.fb-btn:disabled{opacity:.6;cursor:not-allowed}
.fb-btn-cancel{background:var(--bg-primary,#f0f0f0);color:var(--text-secondary,#666)}
.fb-btn-cancel:hover{background:#e2e2e2}
.fb-btn-submit{background:#ef4444;color:#fff}
.fb-btn-submit:hover:not(:disabled){background:#dc2626}
.fb-status{font-size:.85rem;text-align:center;padding:4px 0;min-height:1.5em}
.fb-status-error{color:#ef4444}
.fb-status-ok{color:#22c55e}
[data-theme="dark"] .fb-highlight-layer{background:rgba(255,255,255,.04)}
[data-theme="dark"] .fb-panel{background:rgba(26,26,46,.5);box-shadow:-4px 0 24px rgba(0,0,0,.4)}
[data-theme="dark"] .fb-close:hover{background:rgba(255,255,255,.1)}
[data-theme="dark"] .fb-btn-cancel{background:rgba(255,255,255,.1);color:#ccc}
[data-theme="dark"] .fb-btn-cancel:hover{background:rgba(255,255,255,.15)}
`;
        document.head.appendChild(s);
    }

    /* ── build the overlay DOM (hidden) ── */
    function buildOverlay() {
        if (overlayEl) return;
        injectStyles();

        overlayEl = document.createElement('div');
        overlayEl.id = 'feedback-overlay';
        overlayEl.innerHTML = `
            <div class="fb-highlight-layer" id="fb-highlight-layer">
                <div class="fb-highlight-box" id="fb-highlight-box"></div>
            </div>
            <div class="fb-panel" id="fb-panel">
                <div class="fb-panel-header">
                    <h3>� ${t('title')}</h3>
                    <button class="fb-close" id="fb-close-btn" title="${t('cancel')}">✕</button>
                </div>
                <p class="fb-hint">${t('highlight_hint')}</p>
                <label class="fb-label">${t('category')}</label>
                <select id="fb-category" class="fb-select">
                    <option value="bug">${t('bug')}</option>
                    <option value="suggestion">${t('suggestion')}</option>
                    <option value="question">${t('question')}</option>
                    <option value="other">${t('other')}</option>
                </select>
                <label class="fb-label">${t('description')}</label>
                <textarea id="fb-description" class="fb-textarea" rows="4"
                    placeholder="${t('placeholder')}"></textarea>
                <div class="fb-actions">
                    <button class="fb-btn fb-btn-cancel" id="fb-cancel-btn">${t('cancel')}</button>
                    <button class="fb-btn fb-btn-submit" id="fb-submit-btn">${t('submit')}</button>
                </div>
                <div class="fb-status" id="fb-status"></div>
            </div>
        `;

        document.body.appendChild(overlayEl);

        /* ── event wiring ── */
        const highlightBox = document.getElementById('fb-highlight-box');

        // Listen on document so drawing works OVER the panel too
        document.addEventListener('mousedown', (e) => {
            if (!overlayEl || !overlayEl.classList.contains('active')) return;
            // Don't start drawing on interactive panel elements
            if (e.target.closest('button, input, textarea, select, label, a, .fb-close')) return;
            isDrawing = true;
            startX = e.clientX;
            startY = e.clientY;
            highlightBox.style.display = 'block';
            highlightBox.style.left = startX + 'px';
            highlightBox.style.top = startY + 'px';
            highlightBox.style.width = '0';
            highlightBox.style.height = '0';
            e.preventDefault(); // prevent text selection while drawing
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDrawing) return;
            const x = Math.min(e.clientX, startX);
            const y = Math.min(e.clientY, startY);
            const w = Math.abs(e.clientX - startX);
            const h = Math.abs(e.clientY - startY);
            highlightBox.style.left = x + 'px';
            highlightBox.style.top = y + 'px';
            highlightBox.style.width = w + 'px';
            highlightBox.style.height = h + 'px';
            rect = { x, y, w, h };
        });

        document.addEventListener('mouseup', () => {
            isDrawing = false;
        });

        document.getElementById('fb-close-btn').addEventListener('click', closeFeedback);
        document.getElementById('fb-cancel-btn').addEventListener('click', closeFeedback);
        document.getElementById('fb-submit-btn').addEventListener('click', submitFeedback);

        // Esc to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && overlayEl.classList.contains('active')) closeFeedback();
        });
    }

    /* ── Ctrl+Shift+F global hotkey to toggle feedback widget ── */
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.shiftKey && (e.key === 'F' || e.key === 'f')) {
            e.preventDefault();
            e.stopPropagation();
            console.log('[feedback] Ctrl+Shift+F detected, toggling widget');
            if (overlayEl && overlayEl.classList.contains('active')) {
                closeFeedback();
            } else {
                window.openFeedbackWidget();
            }
        }
    });

    /* ── open / close ── */
    window.openFeedbackWidget = function () {
        buildOverlay();
        rect = { x: 0, y: 0, w: 0, h: 0 };
        document.getElementById('fb-highlight-box').style.display = 'none';
        document.getElementById('fb-description').value = '';
        document.getElementById('fb-category').value = 'bug';
        document.getElementById('fb-status').textContent = '';
        document.getElementById('fb-status').className = 'fb-status';
        document.getElementById('fb-submit-btn').disabled = false;
        document.getElementById('fb-submit-btn').textContent = t('submit');
        overlayEl.classList.add('active');
        // Focus description after a short delay (let animation finish)
        setTimeout(() => document.getElementById('fb-description').focus(), 200);
    };

    function closeFeedback() {
        if (overlayEl) overlayEl.classList.remove('active');
    }

    /* ── submit ── */
    async function submitFeedback() {
        const desc = document.getElementById('fb-description').value.trim();
        const cat = document.getElementById('fb-category').value;
        const statusEl = document.getElementById('fb-status');
        const submitBtn = document.getElementById('fb-submit-btn');

        if (!desc) {
            statusEl.textContent = t('description_required');
            statusEl.className = 'fb-status fb-status-error';
            document.getElementById('fb-description').focus();
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = t('sending');
        statusEl.textContent = '';

        let screenshotData = null;

        // Hide the overlay temporarily for the screenshot
        overlayEl.style.display = 'none';

        try {
            if (typeof html2canvas === 'function') {
                const canvas = await html2canvas(document.body, {
                    useCORS: true,
                    logging: false,
                    scale: Math.min(window.devicePixelRatio || 1, 2),
                    width: window.innerWidth,
                    height: window.innerHeight,
                    x: window.scrollX,
                    y: window.scrollY,
                });

                // If user drew a highlight, draw it on the canvas
                if (rect.w > 5 && rect.h > 5) {
                    const ctx = canvas.getContext('2d');
                    const dpr = canvas.width / window.innerWidth;
                    ctx.strokeStyle = '#ef4444';
                    ctx.lineWidth = 3 * dpr;
                    ctx.setLineDash([8 * dpr, 4 * dpr]);
                    ctx.strokeRect(
                        rect.x * dpr, rect.y * dpr,
                        rect.w * dpr, rect.h * dpr
                    );
                    // Semi-transparent tint outside the box
                    ctx.fillStyle = 'rgba(0,0,0,0.25)';
                    // Top
                    ctx.fillRect(0, 0, canvas.width, rect.y * dpr);
                    // Bottom
                    ctx.fillRect(0, (rect.y + rect.h) * dpr, canvas.width, canvas.height - (rect.y + rect.h) * dpr);
                    // Left
                    ctx.fillRect(0, rect.y * dpr, rect.x * dpr, rect.h * dpr);
                    // Right
                    ctx.fillRect((rect.x + rect.w) * dpr, rect.y * dpr, canvas.width - (rect.x + rect.w) * dpr, rect.h * dpr);
                }

                screenshotData = canvas.toDataURL('image/png', 0.8);
            }
        } catch (err) {
            console.warn('Screenshot capture failed:', err);
        }

        // Show overlay again
        overlayEl.style.display = '';

        const payload = {
            url: window.location.href,
            description: desc,
            category: cat,
            screenshot: screenshotData,
            annotation: (rect.w > 5 && rect.h > 5) ? rect : null,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight,
                dpr: window.devicePixelRatio || 1,
            },
        };

        try {
            const res = await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            // Show success
            statusEl.innerHTML = `<strong>${t('success_title')}</strong> ${t('success_msg')}`;
            statusEl.className = 'fb-status fb-status-ok';
            submitBtn.textContent = '✓';

            // Auto-close after 2s
            setTimeout(closeFeedback, 2000);
        } catch (err) {
            statusEl.textContent = t('error');
            statusEl.className = 'fb-status fb-status-error';
            submitBtn.disabled = false;
            submitBtn.textContent = t('submit');
        }
    }
})();

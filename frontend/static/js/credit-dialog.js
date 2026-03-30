/**
 * credit-dialog.js — Credit confirmation + insufficient-balance dialogs
 *
 * Usage:
 *   // Pre-check then confirm:
 *   confirmCreditSpend('match_report', 'Clara match report', function() {
 *     // user confirmed — proceed with the API call
 *     fetch('/api/matches/123/456/enrich', { method: 'POST' });
 *   });
 *
 *   // Handle 402 responses:
 *   handleInsufficientCredit(errorDetail);
 */
(function () {
  'use strict';

  var overlay = null;

  function ensureOverlay() {
    if (overlay) return;
    overlay = document.createElement('div');
    overlay.id = 'credit-dialog-overlay';
    overlay.innerHTML =
      '<div id="credit-dialog">' +
        '<div id="credit-dialog-icon"></div>' +
        '<h3 id="credit-dialog-title"></h3>' +
        '<p id="credit-dialog-msg"></p>' +
        '<div id="credit-dialog-actions"></div>' +
      '</div>';
    overlay.style.cssText =
      'position:fixed;inset:0;z-index:10001;display:none;align-items:center;' +
      'justify-content:center;background:rgba(0,0,0,.4);';

    var dialog = overlay.querySelector('#credit-dialog');
    dialog.style.cssText =
      'background:var(--card-bg,#fff);border-radius:16px;padding:28px 24px 20px;' +
      'max-width:400px;width:90%;text-align:center;' +
      'box-shadow:0 8px 32px rgba(0,0,0,.2);font-family:inherit;' +
      'animation:cdFadeIn .2s ease;';
    overlay.querySelector('#credit-dialog-icon').style.cssText =
      'font-size:2.2rem;margin-bottom:8px;';
    overlay.querySelector('#credit-dialog-title').style.cssText =
      'margin:0 0 8px;font-size:1.1rem;color:var(--text-primary,#222);';
    overlay.querySelector('#credit-dialog-msg').style.cssText =
      'font-size:0.92rem;line-height:1.55;color:var(--text-secondary,#555);margin:0 0 20px;';
    overlay.querySelector('#credit-dialog-actions').style.cssText =
      'display:flex;gap:10px;justify-content:center;flex-wrap:wrap;';

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) hide();
    });

    var style = document.createElement('style');
    style.textContent =
      '@keyframes cdFadeIn{from{opacity:0;transform:scale(.94)}to{opacity:1;transform:scale(1)}}' +
      '#credit-dialog button{border:none;padding:10px 24px;border-radius:8px;' +
      'font-size:0.92rem;cursor:pointer;font-weight:500;}' +
      '#credit-dialog .cd-confirm{background:var(--teal,#2d9f8f);color:#fff;}' +
      '#credit-dialog .cd-cancel{background:var(--bg-muted,#eee);color:var(--text-primary,#333);}' +
      '#credit-dialog .cd-topup{background:var(--teal,#2d9f8f);color:#fff;}';
    document.head.appendChild(style);
    document.body.appendChild(overlay);
  }

  function hide() {
    if (overlay) overlay.style.display = 'none';
  }

  function show(icon, title, msg, buttons) {
    ensureOverlay();
    overlay.querySelector('#credit-dialog-icon').textContent = icon;
    overlay.querySelector('#credit-dialog-title').textContent = title;
    overlay.querySelector('#credit-dialog-msg').textContent = msg;

    var actions = overlay.querySelector('#credit-dialog-actions');
    actions.innerHTML = '';
    buttons.forEach(function (b) {
      var btn = document.createElement('button');
      btn.className = b.cls || '';
      btn.textContent = b.label;
      btn.addEventListener('click', function () {
        hide();
        if (b.action) b.action();
      });
      actions.appendChild(btn);
    });

    overlay.style.display = 'flex';
  }

  /**
   * Pre-check credits, then show confirmation dialog.
   * @param {string} eventType  - 'match_report', 'employer_research'
   * @param {string} label      - Human label: "Clara match report"
   * @param {function} onConfirm - Called if user confirms
   */
  function confirmCreditSpend(eventType, label, onConfirm) {
    fetch('/api/account/credit-check/' + eventType)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.is_sustainer) {
          // Sustainers skip confirmation — just do it
          if (onConfirm) onConfirm();
          return;
        }

        if (!data.allowed) {
          // Insufficient balance
          handleInsufficientCredit(data);
          return;
        }

        // Show confirmation
        var costStr = '€' + data.cost_eur;
        var balStr = '€' + data.balance_eur;
        var afterStr = '€' + (data.balance_after / 100).toFixed(2);

        show(
          '💳',
          label,
          'This costs ' + costStr + ' from your balance of ' + balStr + '.\n' +
          'Balance after: ' + afterStr,
          [
            { label: 'Cancel', cls: 'cd-cancel' },
            { label: 'Confirm ' + costStr, cls: 'cd-confirm', action: onConfirm },
          ]
        );
      })
      .catch(function (err) {
        console.error('Credit check failed:', err);
        // Fallback: let the API call handle it
        if (onConfirm) onConfirm();
      });
  }

  /**
   * Show "insufficient balance" dialog with top-up CTA.
   * @param {object} detail - { cost_cents, balance_cents, message }
   */
  function handleInsufficientCredit(detail) {
    var msg = detail.message || 'Insufficient credits.';
    show(
      '💸',
      'Insufficient Balance',
      msg,
      [
        { label: 'Cancel', cls: 'cd-cancel' },
        {
          label: '💳 Top Up Credits',
          cls: 'cd-topup',
          action: function () { window.location.href = '/account#credits'; }
        },
      ]
    );
  }

  window.confirmCreditSpend = confirmCreditSpend;
  window.handleInsufficientCredit = handleInsufficientCredit;
})();

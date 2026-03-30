/**
 * placeholder-dialog.js — "Coming soon" dialogs for paid features
 *
 * Usage:
 *   showPlaceholderDialog('clara_report', 'Clara reports will be available soon...');
 *   showPlaceholderDialog('top_up', message, { emoji: '💳' });
 */
(function () {
  'use strict';

  var overlay = null;

  function create() {
    if (overlay) return;
    overlay = document.createElement('div');
    overlay.id = 'ph-dialog-overlay';
    overlay.innerHTML =
      '<div id="ph-dialog">' +
        '<div id="ph-dialog-emoji"></div>' +
        '<p id="ph-dialog-msg"></p>' +
        '<button id="ph-dialog-close">OK</button>' +
      '</div>';
    overlay.style.cssText =
      'position:fixed;inset:0;z-index:10000;display:none;align-items:center;' +
      'justify-content:center;background:rgba(0,0,0,.35);';
    var dialog = overlay.querySelector('#ph-dialog');
    dialog.style.cssText =
      'background:#fff;border-radius:16px;padding:32px 28px 24px;max-width:380px;' +
      'width:90%;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,.18);' +
      'font-family:inherit;animation:phFadeIn .2s ease;';
    overlay.querySelector('#ph-dialog-emoji').style.cssText =
      'font-size:2.4rem;margin-bottom:12px;';
    overlay.querySelector('#ph-dialog-msg').style.cssText =
      'font-size:1rem;line-height:1.55;color:#333;margin:0 0 20px;';
    var btn = overlay.querySelector('#ph-dialog-close');
    btn.style.cssText =
      'background:var(--teal,#2d9f8f);color:#fff;border:none;padding:10px 32px;' +
      'border-radius:8px;font-size:0.95rem;cursor:pointer;';
    btn.addEventListener('click', hide);
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) hide();
    });

    var style = document.createElement('style');
    style.textContent = '@keyframes phFadeIn{from{opacity:0;transform:scale(.95)}to{opacity:1;transform:scale(1)}}';
    document.head.appendChild(style);
    document.body.appendChild(overlay);
  }

  function hide() {
    if (overlay) overlay.style.display = 'none';
  }

  /**
   * @param {string} feature  - e.g. 'clara_report', 'doug_research', 'top_up', 'sustainer'
   * @param {string} message  - user-visible message
   * @param {object} [opts]   - { emoji: '🌿' }
   */
  function showPlaceholderDialog(feature, message, opts) {
    create();
    var emoji = (opts && opts.emoji) || '🌿';
    overlay.querySelector('#ph-dialog-emoji').textContent = emoji;
    overlay.querySelector('#ph-dialog-msg').textContent = message;
    overlay.style.display = 'flex';

    // Log demand signal — fire-and-forget
    try {
      fetch('/api/events/track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_type: 'placeholder_click', event_data: { feature: feature } })
      }).catch(function () {});
    } catch (_) {}
  }

  window.showPlaceholderDialog = showPlaceholderDialog;
})();

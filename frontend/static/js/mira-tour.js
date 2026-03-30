/**
 * mira-tour.js — Per-page mini-tours using Driver.js
 *
 * Each page/tab can have its own walkthrough triggered:
 *   1. Automatically on first visit (stored per page in localStorage)
 *   2. Manually via the tour button in Mira's widget
 *
 * Depends on: Driver.js (loaded via CDN in base.html)
 */
(function () {
  'use strict';

  // ── Tour configurations per page:tab ──────────────────────────
  var TOURS = {
    '/search:situation': [
      {
        element: '#flip-cards-row',
        popover: {
          title: '🧭 Deine Situation',
          description: 'Diese Karten helfen uns, deine Situation zu verstehen. Dreh jede um und beantworte die Frage.',
          side: 'bottom',
          align: 'center'
        }
      },
      {
        element: '#search-player',
        popover: {
          title: '🎮 Player-Leiste',
          description: 'Benutze diesen Player, um zwischen den Suchschritten zu wechseln. Klick auf den Pfeil, um weiterzugehen.',
          side: 'top',
          align: 'center'
        }
      }
    ],
    '/search:direction': [
      {
        element: '.kanban-column, .fk-column',
        popover: {
          title: '💼 Berufsfelder sortieren',
          description: 'Hier sortierst du Berufsfelder nach Interesse. Felder die dich interessieren nach links, die anderen nach rechts. Klick auf ein Feld, um reinzuschauen.',
          side: 'right',
          align: 'start'
        }
      }
    ],
    '/search:level': [
      {
        element: '#ql-strip',
        popover: {
          title: '⭐ Qualifikationsstufe',
          description: 'Wähl die Stufen, die zu deiner Erfahrung passen. Du kannst mehrere auswählen — wenn du keine wählst, siehst du alles.',
          side: 'bottom',
          align: 'center'
        }
      }
    ],
    '/search:location': [
      {
        element: '#search-map',
        popover: {
          title: '📍 Standort wählen',
          description: 'Wähl aus, wo du arbeiten möchtest. Gib eine Stadt ein, klick auf die Karte oder wähl ein Bundesland. Der Kreis zeigt dir deinen Pendelbereich.',
          side: 'left',
          align: 'center'
        }
      }
    ],
    '/search:opportunities': [
      {
        element: '.results-grid, #results-grid',
        popover: {
          title: '🎯 Deine Stellen',
          description: 'Das sind die Stellen, die zu deiner Suche passen. Klick auf eine Stelle, um die Details zu sehen.',
          side: 'top',
          align: 'center'
        }
      }
    ],
    '/search:power': [
      {
        element: '#power-search-layout, .power-layout',
        popover: {
          title: '⚡ Power-Suche',
          description: 'Alle Filter auf einem Bildschirm. Klick auf Kategorien, um sie an- oder abzuwählen.',
          side: 'right',
          align: 'start'
        }
      }
    ],
    '/overview': [
      {
        element: '#journey-zone, .journey-flowchart',
        popover: {
          title: '🗺️ Deine Reise',
          description: 'Oben siehst du, wo du in deiner Jobsuche stehst. Siehst du den nächsten Schritt? Klick drauf.',
          side: 'bottom',
          align: 'center'
        }
      }
    ],
    '/profile': [
      {
        element: '.pb-content, .profile-panes',
        popover: {
          title: '📋 Dein Profil',
          description: 'Das ist dein Profil. Drei Wege zum Einrichten — Lebenslauf hochladen, mit Mira chatten oder das Formular ausfüllen.',
          side: 'left',
          align: 'start'
        }
      }
    ],
    '/messages': [
      {
        element: '.conversation-list, .msg-list',
        popover: {
          title: '💬 Dein Postfach',
          description: 'Hier kannst du mit deinen KI-Assistenten chatten und Nachrichten vom Support erhalten. Wähl links ein Gespräch aus.',
          side: 'right',
          align: 'start'
        }
      }
    ],
    '/account': [
      {
        element: '.account-container',
        popover: {
          title: '⚙️ Einstellungen',
          description: 'Hier verwaltest du dein Konto — Sprache, E-Mail-Einstellungen, Datenschutz. Nichts Dringendes, aber gut zu wissen.',
          side: 'right',
          align: 'start'
        }
      }
    ]
  };

  // ── localStorage key per page ─────────────────────────────────
  function tourKey(pageId) {
    return 'mira_tour_completed_' + pageId.replace(/[^a-z0-9]/gi, '_');
  }

  function isTourDone(pageId) {
    return localStorage.getItem(tourKey(pageId)) === 'true';
  }

  function markTourDone(pageId) {
    localStorage.setItem(tourKey(pageId), 'true');
  }

  // ── Resolve which tour applies to current page ────────────────
  function resolvePageId() {
    var path = window.location.pathname.replace(/\/$/, '') || '/';

    // On search page, include current tab
    if (path === '/search') {
      var activeTab = document.querySelector('.pill-btn.active');
      var tab = activeTab ? activeTab.dataset.tab : 'situation';
      return '/search:' + tab;
    }
    return path;
  }

  // ── Run a mini-tour ───────────────────────────────────────────
  function runTour(pageId) {
    if (!window.driver || !window.driver.js) return;

    var steps = TOURS[pageId];
    if (!steps || !steps.length) return;

    // Filter steps whose targets actually exist in the DOM
    var validSteps = steps.filter(function (s) {
      return !s.element || document.querySelector(s.element);
    });
    if (!validSteps.length) return;

    var d = window.driver.js.driver({
      showProgress: true,
      progressText: '{{current}} von {{total}}',
      nextBtnText: 'Weiter →',
      prevBtnText: '← Zurück',
      doneBtnText: 'Verstanden!',
      allowClose: true,
      overlayColor: 'rgba(0, 0, 0, 0.35)',
      stagePadding: 10,
      stageRadius: 8,
      popoverClass: 'mira-tour-popover',
      onDestroyStarted: function () {
        markTourDone(pageId);
        d.destroy();
      }
    });

    d.setSteps(validSteps);
    d.drive();
  }

  // ── Auto-start on first visit (unless user opted out) ─────────
  function autoStart() {
    if (localStorage.getItem('mira_auto_tour_disabled') === 'true') return;

    var pageId = resolvePageId();
    if (isTourDone(pageId)) return;

    // Give the page time to settle
    setTimeout(function () {
      runTour(pageId);
    }, 3000);
  }

  // ── Expose global API ─────────────────────────────────────────
  window.miraTour = {
    run: function (pageId) {
      pageId = pageId || resolvePageId();
      runTour(pageId);
    },
    reset: function (pageId) {
      pageId = pageId || resolvePageId();
      localStorage.removeItem(tourKey(pageId));
    },
    resetAll: function () {
      Object.keys(TOURS).forEach(function (k) {
        localStorage.removeItem(tourKey(k));
      });
    }
  };

  // Wait for DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoStart);
  } else {
    autoStart();
  }
})();

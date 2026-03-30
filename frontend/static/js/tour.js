/**
 * Mira's Interactive Tour
 * Uses Driver.js for guided onboarding
 * 
 * Trigger: First login only (stored in localStorage)
 * Scope: Core flow - Home → Overview → Jobs → Messages → Mira Chat
 */

// Tour configuration with Mira's personality
const MIRA_TOUR_STEPS = [
    {
        popover: {
            title: '🧘 Willkommen bei talent.yoga!',
            description: `
                <div class="mira-tour-content">
                    <p>Schön, dass du da bist! Lass uns einen kurzen Rundgang machen.</p>
                    <p>Wir zeigen dir die wichtigsten Funktionen — und am Ende lernst du <strong>Mira</strong> kennen, deine persönliche Karrierebegleiterin.</p>
                    <p class="mira-tour-action">Klick auf <strong>Weiter</strong>, um die Tour zu starten.</p>
                    <p class="mira-tour-hint">Klick auf <strong>Abbrechen</strong> um die Tour zu überspringen — du kannst sie jederzeit über Tour in der Seitenleiste starten:</p>
                    <p class="mira-tour-sidebar-icon">🎓</p>
                </div>
            `,
            side: 'center',
            align: 'center'
        }
    },
    {
        element: 'a[href="/dashboard"]',
        popover: {
            title: '🏠 Dein Startpunkt',
            description: `
                <div class="mira-tour-content">
                    <p>Das ist deine <strong>Startseite</strong>. Hier findest du:</p>
                    <ul>
                        <li>Deine wichtigsten Statistiken</li>
                        <li>Nächste Schritte</li>
                        <li>Aktuelle Benachrichtigungen</li>
                    </ul>
                </div>
            `,
            side: 'right',
            align: 'start'
        },
        disableActiveInteraction: true
    },
    {
        element: 'a[href="/profile"]',
        popover: {
            title: '📋 Dein Profil',
            description: `
                <div class="mira-tour-content">
                    <p>Hier erstellst du dein <strong>Profil</strong>:</p>
                    <ul>
                        <li>Lebenslauf hochladen oder manuell eingeben</li>
                        <li>Je vollständiger, desto bessere Matches!</li>
                    </ul>
                </div>
            `,
            side: 'right',
            align: 'start'
        },
        disableActiveInteraction: true
    },
    {
        element: 'a[href="/matches"]',
        popover: {
            title: '💼 Stellenangebote',
            description: `
                <div class="mira-tour-content">
                    <p>Das <strong>Herzstück</strong> von talent.yoga!</p>
                    <p>Hier findest du alle Jobs, die zu deinem Profil passen — sortiert nach Übereinstimmung.</p>
                    <ul>
                        <li>🎯 Match-Score zeigt, wie gut der Job passt</li>
                        <li>⭐ Speichere interessante Jobs</li>
                        <li>📝 Bewirb dich direkt</li>
                    </ul>
                </div>
            `,
            side: 'right',
            align: 'start'
        },
        disableActiveInteraction: true
    },
    {
        element: 'a[href="/messages"]',
        popover: {
            title: '💬 Nachrichten',
            description: `
                <div class="mira-tour-content">
                    <p>Dein <strong>persönlicher Posteingang</strong>.</p>
                    <p>Hier kommunizierst du mit dem talent.yoga Team:</p>
                    <ul>
                        <li>🧘 Mira — deine Karrierebegleiterin</li>
                        <li>📰 Doug — Newsletter & Updates</li>
                    </ul>
                </div>
            `,
            side: 'right',
            align: 'start'
        },
        disableActiveInteraction: true
    },
    {
        element: '.mira-fab, #mira-widget .mira-fab',
        popover: {
            title: '🧘 Das ist Mira!',
            description: `
                <div class="mira-tour-content">
                    <p><strong>Mira</strong> ist deine persönliche Begleiterin bei talent.yoga.</p>
                    <p>Du kannst sie jederzeit über diesen Button erreichen — sie hilft dir bei:</p>
                    <ul>
                        <li>Fragen zur Jobsuche</li>
                        <li>Deinem Profil verbessern</li>
                        <li>Bewerbungstipps</li>
                    </ul>
                    <p>Nach der Tour stellt sie sich persönlich vor!</p>
                </div>
            `,
            side: 'left',
            align: 'end'
        },
        disableActiveInteraction: true
    },
    {
        popover: {
            title: '🎉 Du bist startklar!',
            description: `
                <div class="mira-tour-content">
                    <p>Das war's! Du kennst jetzt die wichtigsten Funktionen.</p>
                    <p><strong>Nächster Schritt:</strong> Fülle dein Profil aus — je mehr Mira über dich weiß, desto besser kann sie passende Jobs finden!</p>
                    <p>Mira meldet sich gleich bei dir. Viel Erfolg! 💪</p>
                </div>
            `,
            side: 'center',
            align: 'center'
        }
    }
];

// Initialize Driver.js with custom styling
function initMiraTour() {
    // Driver.js IIFE exposes as window.driver.js.driver()
    if (typeof window.driver === 'undefined' || typeof window.driver.js === 'undefined') {
        console.warn('Driver.js not loaded');
        return null;
    }

    let destroying = false;
    
    const driverObj = window.driver.js.driver({
        showProgress: true,
        progressText: '{{current}} von {{total}}',
        nextBtnText: 'Weiter →',
        prevBtnText: '← Zurück',
        doneBtnText: 'Fertig!',
        allowClose: true,
        overlayColor: 'rgba(0, 0, 0, 0.35)',
        stagePadding: 10,
        stageRadius: 8,
        popoverClass: 'mira-tour-popover',
        
        onDestroyStarted: () => {
            if (destroying) return;
            destroying = true;
            // Mark tour as completed
            localStorage.setItem('mira_tour_completed', 'true');
            localStorage.setItem('mira_tour_completed_at', new Date().toISOString());
            window._tourActive = false;
            driverObj.destroy();
            // Show Mira widget again and open chat with greeting
            const miraWidget = document.getElementById('mira-widget');
            if (miraWidget) miraWidget.style.display = '';
            // After tour ends, open Mira chat with a friendly hello
            setTimeout(() => {
                if (typeof triggerMiraGreeting === 'function') {
                    triggerMiraGreeting();
                }
            }, 600);
        },
        
        onPopoverRender: (popover, { state }) => {
            setTimeout(() => {
                // --- Move Abbrechen (close btn) into footer left ---
                const footer = document.querySelector('.driver-popover-footer');
                const closeBtn = document.querySelector('.driver-popover-close-btn');
                if (footer && closeBtn && !closeBtn.dataset.moved) {
                    closeBtn.textContent = 'Abbrechen';
                    closeBtn.classList.add('driver-popover-cancel-btn');
                    closeBtn.dataset.moved = 'true';
                    footer.insertBefore(closeBtn, footer.firstChild);
                }
                // On first step, hide the disabled prev button
                const prevBtn = document.querySelector('.driver-popover-prev-btn');
                if (prevBtn && prevBtn.disabled) {
                    prevBtn.style.display = 'none';
                }

                // --- Inline progress into title as "Title (N von T)" ---
                const progress = document.querySelector('.driver-popover-progress-text');
                const titleEl = document.querySelector('.driver-popover-title');
                if (progress && titleEl) {
                    // Strip any previously appended progress span
                    const old = titleEl.querySelector('.tour-progress-inline');
                    if (old) old.remove();
                    const span = document.createElement('span');
                    span.className = 'tour-progress-inline';
                    span.textContent = ` (${progress.textContent.trim()})`;
                    titleEl.appendChild(span);
                    progress.style.display = 'none';
                }
            }, 50);

            // Step 0 (welcome screen) — spotlight the tour button
            if ((state?.activeIndex ?? 0) === 0) {
                setTimeout(spotlightTourButton, 400);
            }
        },
        
        onHighlightStarted: (element, step, options) => {
            // Tour step tracking (silent)
        }
    });

    return driverObj;
}

// Track whether any user interaction has happened since page load.
// If so, skip the spotlight — user clearly knows their way around.
let _userInteracted = false;
let _tourAutoStart = false;
['click', 'keydown', 'touchstart'].forEach(evt =>
    window.addEventListener(evt, () => { _userInteracted = true; }, { once: true, capture: true })
);

// Start tour. autoStart=true when triggered automatically on first visit;
// false when the user clicked the tour button themselves.
function startMiraTour(autoStart = false) {
    _tourAutoStart = autoStart;
    window._tourActive = true;
    // Collapse Mira chat during tour (keep FAB visible for the intro step)
    const miraWidget = document.getElementById('mira-widget');
    if (miraWidget) miraWidget.classList.remove('open');

    const driverObj = initMiraTour();
    if (driverObj) {
        driverObj.setSteps(MIRA_TOUR_STEPS);
        driverObj.drive();
    }
}

// Spotlight the tour button in the sidebar (step 0 — the welcome screen
// that mentions "🎓 Tour in der Seitenleiste").
// Only fires on auto-start AND only if the user hasn't already interacted.
function spotlightTourButton() {
    if (!_tourAutoStart || _userInteracted) return;
    const btn = document.querySelector('a.nav-item[data-tooltip="Tour starten"]');
    if (!btn) return;
    btn.classList.add('tour-btn-spotlight');
    setTimeout(() => btn.classList.remove('tour-btn-spotlight'), 3200);
}

// Check if should auto-start tour
function checkAutoStartTour() {
    // Only on overview page (was dashboard)
    if (!window.location.pathname.includes('/overview')) {
        return;
    }
    
    // Check if tour was already completed
    const tourCompleted = localStorage.getItem('mira_tour_completed');
    if (tourCompleted === 'true') {
        return;
    }
    
    // Give the page 5 seconds to breathe before surprising the yogi
    setTimeout(() => {
        startMiraTour(true);  // autoStart=true → enables spotlight animation
    }, 5000);
}

// Manual trigger from help menu or button
window.startMiraTour = startMiraTour;

// Reset tour (for testing or if user wants to see it again)
window.resetMiraTour = function() {
    localStorage.removeItem('mira_tour_completed');
    localStorage.removeItem('mira_tour_completed_at');
};

// Auto-start on page load
document.addEventListener('DOMContentLoaded', checkAutoStartTour);

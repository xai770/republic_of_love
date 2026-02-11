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
                    <p>Hallo! Ich bin <strong>Mira</strong>, deine persönliche Karrierebegleiterin.</p>
                    <p>Lass mich dir zeigen, wie du talent.yoga nutzen kannst, um deinen Traumjob zu finden!</p>
                    <p class="mira-tour-action">Klick auf <strong>Weiter</strong>, um die Tour zu starten.</p>
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
                        <li>Meine persönliche Begrüßung</li>
                        <li>Deine wichtigsten Statistiken</li>
                        <li>Nächste Schritte, die ich für dich empfehle</li>
                    </ul>
                    <p class="mira-tour-action">Klick auf diesen Button!</p>
                </div>
            `,
            side: 'right',
            align: 'start'
        }
    },
    {
        element: 'a[href="/bi"]',
        popover: {
            title: '📊 Meine Übersicht',
            description: `
                <div class="mira-tour-content">
                    <p>Hier siehst du den <strong>großen Überblick</strong>:</p>
                    <ul>
                        <li>Wie vollständig ist dein Profil?</li>
                        <li>Wie viele Jobs passen zu dir?</li>
                        <li>Deine Aktivitäten auf einen Blick</li>
                    </ul>
                    <p class="mira-tour-action">Klick hier, um deine Übersicht zu sehen!</p>
                </div>
            `,
            side: 'right',
            align: 'start'
        }
    },
    {
        element: 'a[href="/matches"]',
        popover: {
            title: '💼 Meine Stellenangebote',
            description: `
                <div class="mira-tour-content">
                    <p>Das <strong>Herzstück</strong> von talent.yoga!</p>
                    <p>Hier findest du alle Jobs, die zu deinem Profil passen. Ich sortiere sie nach Übereinstimmung.</p>
                    <ul>
                        <li>🎯 Match-Score zeigt, wie gut der Job passt</li>
                        <li>⭐ Speichere interessante Jobs</li>
                        <li>📝 Bewirb dich direkt</li>
                    </ul>
                    <p class="mira-tour-action">Klick hier, um deine Matches zu entdecken!</p>
                </div>
            `,
            side: 'right',
            align: 'start'
        }
    },
    {
        element: 'a[href="/messages"]',
        popover: {
            title: '💬 Nachrichten',
            description: `
                <div class="mira-tour-content">
                    <p>Dein <strong>persönlicher Posteingang</strong>.</p>
                    <p>Hier kannst du mit mir und dem gesamten talent.yoga Team kommunizieren:</p>
                    <ul>
                        <li>🧘 Mira — Karrieretipps & Fragen</li>
                        <li>📰 Doug — Newsletter & Updates</li>
                        <li>🔮 Arden — Tiefe Einsichten</li>
                    </ul>
                    <p class="mira-tour-action">Klick hier, um deine Nachrichten zu sehen!</p>
                </div>
            `,
            side: 'right',
            align: 'start'
        }
    },
    {
        element: '.mira-fab, #mira-widget .mira-fab',
        popover: {
            title: '🧘 Frag mich jederzeit!',
            description: `
                <div class="mira-tour-content">
                    <p>Das bin ich — dein <strong>Chat-Button</strong>!</p>
                    <p>Klick hier, wenn du Fragen hast. Ich helfe dir gerne bei:</p>
                    <ul>
                        <li>Deinem Lebenslauf verbessern</li>
                        <li>Jobs besser verstehen</li>
                        <li>Bewerbungstipps</li>
                        <li>Oder einfach zum Plaudern 😊</li>
                    </ul>
                    <p class="mira-tour-action">Probier es aus — klick auf den Chat!</p>
                </div>
            `,
            side: 'left',
            align: 'end'
        }
    },
    {
        popover: {
            title: '🎉 Du bist startklar!',
            description: `
                <div class="mira-tour-content">
                    <p>Das war's! Du kennst jetzt die wichtigsten Funktionen.</p>
                    <p><strong>Mein Tipp:</strong> Beginne damit, dein Profil vollständig auszufüllen. Je mehr ich über dich weiß, desto besser kann ich passende Jobs finden!</p>
                    <p>Ich bin immer für dich da. Viel Erfolg bei deiner Jobsuche! 💪</p>
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

    const driverObj = window.driver.js.driver({
        showProgress: true,
        progressText: '{{current}} von {{total}}',
        nextBtnText: 'Weiter →',
        prevBtnText: '← Zurück',
        doneBtnText: 'Fertig!',
        allowClose: true,
        overlayColor: 'rgba(0, 0, 0, 0.75)',
        stagePadding: 10,
        stageRadius: 8,
        popoverClass: 'mira-tour-popover',
        
        onDestroyStarted: () => {
            // Mark tour as completed
            localStorage.setItem('mira_tour_completed', 'true');
            localStorage.setItem('mira_tour_completed_at', new Date().toISOString());
            driverObj.destroy();
        },
        
        onHighlightStarted: (element, step, options) => {
            // Track which step user is on (for analytics later)
            console.log('Tour step:', options.state.activeIndex);
        }
    });

    return driverObj;
}

// Start tour (manual trigger or first-time)
function startMiraTour() {
    const driverObj = initMiraTour();
    if (driverObj) {
        driverObj.setSteps(MIRA_TOUR_STEPS);
        driverObj.drive();
    }
}

// Check if should auto-start tour
function checkAutoStartTour() {
    // Only on dashboard (home page)
    if (!window.location.pathname.includes('/dashboard')) {
        return;
    }
    
    // Check if tour was already completed
    const tourCompleted = localStorage.getItem('mira_tour_completed');
    if (tourCompleted === 'true') {
        return;
    }
    
    // Check if this is first visit (give page time to load)
    setTimeout(() => {
        startMiraTour();
    }, 1000);
}

// Manual trigger from help menu or button
window.startMiraTour = startMiraTour;

// Reset tour (for testing or if user wants to see it again)
window.resetMiraTour = function() {
    localStorage.removeItem('mira_tour_completed');
    localStorage.removeItem('mira_tour_completed_at');
    console.log('Tour reset. Refresh the dashboard to see it again.');
};

// Auto-start on page load
document.addEventListener('DOMContentLoaded', checkAutoStartTour);

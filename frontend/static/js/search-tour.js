/**
 * Mira's Search Page Tour
 * Uses Driver.js for guided walkthrough of the search interface
 *
 * Trigger: First visit to /search (stored in localStorage)
 * Scope: Domain bars → Map → QL → Filter pills → Save → Mira chat
 *
 * i18n: Reads translations from window.SEARCH_TOUR_I18N (injected by template)
 */

function getSearchTourSteps() {
    const t = window.SEARCH_TOUR_I18N || {};

    return [
        // Step 1: Welcome
        {
            popover: {
                title: t.welcome_title || '🔍 Job Search',
                description: `
                    <div class="mira-tour-content">
                        <p>${t.welcome_desc || 'This is where you\'ll find all available positions.'}</p>
                    </div>
                `,
                side: 'center',
                align: 'center'
            }
        },
        // Step 2: Domain bars (left panel)
        {
            element: '.panel-domain',
            popover: {
                title: t.domain_title || '📊 Job Sectors',
                description: `
                    <div class="mira-tour-content">
                        <p>${t.domain_desc || 'Click a sector to filter your search.'}</p>
                    </div>
                `,
                side: 'right',
                align: 'start'
            }
        },
        // Step 3: Map (center panel)
        {
            element: '.panel-map',
            popover: {
                title: t.map_title || '🗺️ The Map',
                description: `
                    <div class="mira-tour-content">
                        <p>${t.map_desc || 'The heatmap shows where jobs are located.'}</p>
                    </div>
                `,
                side: 'left',
                align: 'start'
            }
        },
        // Step 4: Qualification levels (right panel)
        {
            element: '.panel-ql',
            popover: {
                title: t.ql_title || '🎯 Qualification Levels',
                description: `
                    <div class="mira-tour-content">
                        <p>${t.ql_desc || 'Filter by your qualification level.'}</p>
                    </div>
                `,
                side: 'left',
                align: 'start'
            }
        },
        // Step 5: Active filter pills
        {
            element: '.search-header',
            popover: {
                title: t.pills_title || '🏷️ Active Filters',
                description: `
                    <div class="mira-tour-content">
                        <p>${t.pills_desc || 'Your active filters appear here as chips.'}</p>
                    </div>
                `,
                side: 'bottom',
                align: 'start'
            }
        },
        // Step 6: Save button
        {
            element: '.search-actions',
            popover: {
                title: t.save_title || '💾 Save Search',
                description: `
                    <div class="mira-tour-content">
                        <p>${t.save_desc || 'Save your current filter settings.'}</p>
                    </div>
                `,
                side: 'top',
                align: 'start'
            }
        },
        // Step 7: Mira FAB
        {
            element: '.mira-fab, #mira-widget .mira-fab',
            popover: {
                title: t.mira_title || '🧘 Mira helps you!',
                description: `
                    <div class="mira-tour-content">
                        <p>${t.mira_desc || 'Tell Mira what you\'re looking for and she\'ll set filters for you!'}</p>
                    </div>
                `,
                side: 'left',
                align: 'end'
            }
        },
        // Step 8: Done
        {
            popover: {
                title: t.done_title || '🎉 Ready to search!',
                description: `
                    <div class="mira-tour-content">
                        <p>${t.done_desc || 'You now know all the search features. Try it out!'}</p>
                    </div>
                `,
                side: 'center',
                align: 'center'
            }
        }
    ];
}


// Initialize Driver.js for search tour
function initSearchTour() {
    if (typeof window.driver === 'undefined' || typeof window.driver.js === 'undefined') {
        console.warn('Driver.js not loaded');
        return null;
    }

    const t = window.SEARCH_TOUR_I18N || {};

    const driverObj = window.driver.js.driver({
        showProgress: true,
        progressText: t.progress || '{{current}} von {{total}}',
        nextBtnText: t.next || 'Next →',
        prevBtnText: t.prev || '← Back',
        doneBtnText: t.done || "Let's go!",
        allowClose: true,
        overlayColor: 'rgba(0, 0, 0, 0.75)',
        stagePadding: 10,
        stageRadius: 8,
        popoverClass: 'mira-tour-popover',

        onDestroyStarted: () => {
            localStorage.setItem('mira_search_tour_completed', 'true');
            localStorage.setItem('mira_search_tour_completed_at', new Date().toISOString());
            driverObj.destroy();
        },

        onHighlightStarted: (element, step, options) => {
            // Search tour step tracking (silent)
        }
    });

    return driverObj;
}


// Start search tour
function startSearchTour() {
    const driverObj = initSearchTour();
    if (driverObj) {
        driverObj.setSteps(getSearchTourSteps());
        driverObj.drive();
    }
}


// Auto-start on first visit to /search
function checkAutoStartSearchTour() {
    if (!window.location.pathname.includes('/search')) {
        return;
    }

    const completed = localStorage.getItem('mira_search_tour_completed');
    if (completed === 'true') {
        return;
    }

    // Wait for data to load so the panels are populated
    setTimeout(() => {
        startSearchTour();
    }, 2000);
}


// Expose for manual trigger
window.startSearchTour = startSearchTour;

// Reset (for testing)
window.resetSearchTour = function() {
    localStorage.removeItem('mira_search_tour_completed');
    localStorage.removeItem('mira_search_tour_completed_at');
};

// Auto-start on page load
document.addEventListener('DOMContentLoaded', checkAutoStartSearchTour);

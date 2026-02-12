// talent.yoga — Shared JavaScript

// ===== Theme Toggle =====
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    console.log('Theme toggled to:', newTheme);
}

function restoreTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    console.log('Theme restored to:', theme);
}

// Restore theme on DOM ready
restoreTheme();

// ===== Sidebar Toggle =====
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    if (sidebar) sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('show');
}

// ===== HTMX Error Handling =====
document.body.addEventListener('htmx:responseError', function(event) {
    console.error('HTMX error:', event.detail);
    if (event.detail.xhr.status === 401) {
        window.location.href = '/';
    }
});

// ===== Utility Functions =====
function formatDate(dateStr) {
    if (!dateStr) return 'Present';
    return new Date(dateStr).toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short' 
    });
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ===== Event Tracking =====
// Lightweight fire-and-forget events for Mira's behavioral context.
// Not analytics — just enough so Mira knows what the yogi is doing.

function trackEvent(eventType, eventData) {
    try {
        fetch('/api/events/track', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({event_type: eventType, event_data: eventData || {}}),
            credentials: 'same-origin'
        }).catch(() => {}); // fire-and-forget
    } catch(e) { /* silent */ }
}

// Auto-track page_view on every page load
(function() {
    const page = location.pathname;
    // Don't track static assets, API calls, or admin pages
    if (page.startsWith('/api/') || page.startsWith('/static/') || page.startsWith('/admin')) return;
    trackEvent('page_view', {page: page});
})();

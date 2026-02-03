// talent.yoga — Minimal JS (mostly HTMX handles things)

// Handle HTMX errors
document.body.addEventListener('htmx:responseError', function(event) {
    console.error('HTMX error:', event.detail);
    if (event.detail.xhr.status === 401) {
        // Redirect to login on auth failure
        window.location.href = '/';
    }
});

// Format dates nicely
function formatDate(dateStr) {
    if (!dateStr) return 'Present';
    return new Date(dateStr).toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short' 
    });
}

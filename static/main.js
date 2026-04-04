// Theme management
function applyTheme(theme) {
    if (theme === 'light') {
        document.body.classList.add('light-theme');
    } else {
        document.body.classList.remove('light-theme');
    }
    const icon = document.getElementById('themeIcon');
    if (icon) icon.textContent = theme === 'dark' ? '🌙' : '☀️';
}

function toggleTheme() {
    const current = localStorage.getItem('sl_theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('sl_theme', next);
    applyTheme(next);
}

function setTheme(theme) {
    localStorage.setItem('sl_theme', theme);
    applyTheme(theme);
}

// Apply theme immediately on load
document.addEventListener('DOMContentLoaded', () => {
    const theme = localStorage.getItem('sl_theme') || 'dark';
    applyTheme(theme);

    // Auto-dismiss alerts
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 4000);
    });
});

// Apply theme before page paint to avoid flash
(function() {
    const t = localStorage.getItem('sl_theme') || 'dark';
    if (t === 'light') document.documentElement.style.setProperty('--bg','#f0f4f8');
})();

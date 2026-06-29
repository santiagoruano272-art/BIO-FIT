document.addEventListener('DOMContentLoaded', function () {

    // ── MENÚ MÓVIL ───────────────────────────────────────────────────────────
    const menuToggle = document.getElementById('mobile-menu');
    const navLinks   = document.getElementById('nav-links');

    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', function () {
            navLinks.classList.toggle('active');
        });
        navLinks.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                navLinks.classList.remove('active');
            });
        });
    }

    // ── VERIFICACIÓN DE SESIÓN ───────────────────────────────────────────────
    // Páginas públicas donde NO se verifica sesión
    var paginasPublicas = ['/login/', '/registro/', '/terminos/', '/cambiar-password/'];
    var esPublica = paginasPublicas.some(function(p) {
        return window.location.pathname === p;
    });

    if (!esPublica) {
        // sessionStorage se borra automáticamente cuando Edge/Chrome se cierra.
        // Si no existe 'biofit_activo', el navegador fue cerrado → forzar logout.
        if (!sessionStorage.getItem('biofit_activo')) {
            // Destruir sesión en servidor y redirigir
            fetch('/auto-logout/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ source: 'browser_closed' }),
            }).finally(function () {
                window.location.replace('/login/');
            });
        }
    }
});


// ── HELPER CSRF ───────────────────────────────────────────────────────────────
function getCookie(name) {
    var cookieValue = '';
    if (document.cookie && document.cookie !== '') {
        document.cookie.split(';').forEach(function (cookie) {
            var c = cookie.trim();
            if (c.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(c.substring(name.length + 1));
            }
        });
    }
    return cookieValue;
}


// ── LOGOUT MANUAL ─────────────────────────────────────────────────────────────
function logout() {
    sessionStorage.clear();
    localStorage.clear();
    fetch('/auto-logout/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ source: 'manual' }),
    }).finally(function () {
        window.location.replace('/login/');
    });
}
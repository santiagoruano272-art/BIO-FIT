document.addEventListener('DOMContentLoaded', function () {
    var menuToggle = document.getElementById('mobile-menu');
    var navLinks   = document.getElementById('nav-links');

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
});

// Función auxiliar para obtener el token CSRF necesario para el POST de Django
function getCsrfToken() {
    return document.cookie.split(';')
        .map(c => c.trim())
        .find(c => c.startsWith('csrftoken='))
        ?.split('=')[1] || '';
}

async function logout() {
    console.log("🔒 Cerrando sesión en el servidor...");
    try {
        // Le avisamos a Django que destruya la cookie sessionid
        const response = await fetch('/api/logout/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            credentials: 'include' // Crucial para enviar las cookies de sesión actuales
        });

        if (response.ok) {
            console.log("✅ Sesión destruida en backend de forma segura.");
        } else {
            console.warn("⚠️ El backend no destruyó la sesión, forzando limpieza local.");
        }
    } catch (err) {
        console.error("❌ Error conectando con la API de logout:", err);
    } finally {
        // Pase lo que pase, limpiamos el navegador y redirigimos
        localStorage.clear();
        window.location.href = '/login/';
    }
}
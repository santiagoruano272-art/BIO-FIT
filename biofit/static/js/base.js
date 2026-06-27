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

// FUNCIÓN AUXILIAR: Extrae el CSRF Token necesario para peticiones POST seguras en Django
function getCsrfTokenForLogout() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === ('csrftoken=')) {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return cookieValue;
}

// FIX DE FUGA DE SESIÓN: Cierre de sesión sincronizado Cliente <=> Servidor
async function logout() {
    try {
        const csrfToken = getCsrfTokenForLogout();
        
        // 1. Avisar al servidor Django para que destruya el registro en la BD de sesiones e invalide la cookie
        await fetch('/api/logout/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            credentials: 'include' // Obligatorio para enviar e invalidar cookies de sesión activas
        });
        console.log("🔒 Sesión destruida en el servidor Django.");
    } catch (error) {
        console.error("Error al procesar el cierre de sesión en el servidor:", error);
    } finally {
        // 2. Limpiar todo rastro en el almacenamiento del cliente
        localStorage.clear();
        sessionStorage.clear();
        console.log("🧹 Almacenamiento local del navegador limpio.");

        // 3. Redirección final segura al formulario de login limpio
        window.location.href = '/login/';
    }
}
/**
 * base.js - BIO-FIT Ecosistema Global
 * Manejo del menú móvil y cierre de sesión seguro sincronizado con Django.
 */

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

/**
 * Obtiene el token CSRF desde las cookies del navegador.
 */
function getCsrfToken() {
    return document.cookie.split(';')
        .map(c => c.trim())
        .find(c => c.startsWith('csrftoken='))
        ?.split('=')[1] || '';
}

/**
 * Fuerza la eliminación local de la cookie sessionid en el cliente
 * como capa de redundancia ante bucles de redirección.
 */
function borrarCookieSesionLocal() {
    document.cookie = "sessionid=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
}

/**
 * Controla el flujo de Logout destruyendo la sesión en el Backend (Django)
 * y limpiando el almacenamiento local del navegador.
 */
async function logout() {
    console.log("🔒 Iniciando proceso de cierre de sesión unificado...");
    
    try {
        // Enviar petición POST al endpoint de logout en el backend
        const response = await fetch('/api/logout/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            credentials: 'include' // Obligatorio para transmitir las cookies de sesión actuales
        });

        if (response.ok) {
            console.log("✅ Sesión destruida en el backend exitosamente.");
        } else {
            console.warn("⚠️ El backend devolvió un estado no exitoso, forzando cierre local.");
        }
    } catch (err) {
        console.error("❌ Error de red o comunicación con la API de logout:", err);
    } finally {
        // 1. Limpiar credenciales y estados locales
        localStorage.clear();
        sessionStorage.clear();

        // 2. Romper la cookie localmente por seguridad
        borrarCookieSesionLocal();

        console.log("🚀 Redirigiendo limpiamente a la página de login.");
        
        // 3. Redirección estricta eliminando el historial inmediato para evitar botón "Atrás"
        window.location.replace('/login/');
    }
}
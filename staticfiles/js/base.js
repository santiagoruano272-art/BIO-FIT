// FIX: esperar a que el DOM esté listo antes de buscar elementos
document.addEventListener('DOMContentLoaded', function () {
    const menuToggle = document.getElementById('mobile-menu');
    const navLinks = document.getElementById('nav-links');

    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', function () {
            navLinks.classList.toggle('active');
        });

        // Cierra el menú al hacer clic en cualquier enlace
        navLinks.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                navLinks.classList.remove('active');
            });
        });
    }
});

function logout() {
    localStorage.clear();
    window.location.href = '/login/';
}
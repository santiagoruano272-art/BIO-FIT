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

function logout() {
    localStorage.clear();
    window.location.href = '/login/';
}
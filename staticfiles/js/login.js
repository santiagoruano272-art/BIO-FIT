function showAlert(msg, type = 'error') {
    const el = document.getElementById('alertBox');
    if (!el) return;
    el.className = 'alert ' + (type === 'error' ? 'alert-error' : 'alert-success');
    el.textContent = msg;
    el.style.display = 'flex';
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('loginForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email    = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const btn      = document.getElementById('submitBtn');

        btn.textContent = 'Cargando...';
        btn.disabled    = true;

        try {
            const res = await fetch('/api/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                credentials: 'include',
                body: JSON.stringify({ email, password }),
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error('Credenciales incorrectas o usuario no registrado');
            }

            // Limpiar localStorage (sistema anterior)
            localStorage.clear();

            // Guardar en sessionStorage — se borra automáticamente al cerrar Edge/Chrome
            sessionStorage.setItem('biofit_activo', 'true');
            sessionStorage.setItem('biofit_uid',    data.uid);
            sessionStorage.setItem('biofit_email',  email);
            sessionStorage.setItem('biofit_rol',    data.rol);
            sessionStorage.setItem('biofit_token',  data.idToken || data.token || data.uid);

            showAlert('¡Acceso concedido! Entrando...', 'success');

            setTimeout(() => {
                window.location.replace('/');
            }, 1000);

        } catch (err) {
            showAlert(err.message || 'Error en login');
            btn.textContent = 'Entrar';
            btn.disabled    = false;
        }
    });
});
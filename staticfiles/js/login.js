
// ── Utilidades ────────────────────────────────────────────────────────────────

function showAlert(msg, type = 'error', boxId = 'alertBox') {
    const el = document.getElementById(boxId);
    if (!el) return;
    el.className = 'alert ' + (type === 'error' ? 'alert-error' : 'alert-success');
    el.textContent = msg;
    el.style.display = 'flex';
}

function hideAlert(boxId) {
    const el = document.getElementById(boxId);
    if (el) el.style.display = 'none';
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

// Email del paso de recuperación, compartido entre vistas
let _recoveryEmail = '';

// ── Login ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {

    // ── Formulario de login ────────────────────────────────────────────────
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email    = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const btn      = document.getElementById('submitBtn');

            btn.textContent = 'Cargando...';
            btn.disabled    = true;
            hideAlert('alertBox');

            try {
                const res = await fetch('/api/login/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    credentials: 'include',
                    body: JSON.stringify({ email, password }),
                });

                const data = await res.json();

                if (!res.ok) {
                    throw new Error('Credenciales incorrectas o usuario no registrado');
                }

                localStorage.setItem('biofit_token', data.idToken || data.token || data.uid);
                localStorage.setItem('biofit_uid',   data.uid);
                localStorage.setItem('biofit_email', email);
                localStorage.setItem('biofit_rol',   data.rol);

                showAlert('¡Acceso concedido! Entrando...', 'success');
                setTimeout(() => { window.location.href = '/'; }, 1000);

            } catch (err) {
                showAlert(err.message || 'Error en login');
                btn.textContent = 'Entrar';
                btn.disabled    = false;
            }
        });
    }

    // ── Paso 1 de recuperación: enviar código al correo ────────────────────
    const recoveryForm = document.getElementById('recoveryForm');
    if (recoveryForm) {
        recoveryForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('recoveryEmail').value.trim();
            const btn   = document.getElementById('recoveryBtn');

            btn.textContent = 'Enviando...';
            btn.disabled    = true;
            hideAlert('alertBoxRecovery');

            try {
                const res = await fetch('/api/recuperar-password/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    credentials: 'include',
                    body: JSON.stringify({ email }),
                });

                const data = await res.json();

                if (res.status === 429) {
                    showAlert(data.error, 'error', 'alertBoxRecovery');
                    btn.textContent = 'Enviar código';
                    btn.disabled    = false;
                    return;
                }

                if (res.status === 404) {
                    showAlert(data.error, 'error', 'alertBoxRecovery');
                    btn.textContent = 'Enviar código';
                    btn.disabled    = false;
                    return;
                }

                if (!res.ok) {
                    throw new Error(data.error || 'Error al enviar el código');
                }

                // Guardar el email para usarlo en los pasos siguientes
                _recoveryEmail = email;

                // Mostrar panel de éxito dentro de viewRecovery
                recoveryForm.style.display = 'none';
                const successPanel = document.getElementById('recoverySuccess');
                if (successPanel) successPanel.style.display = 'block';

            } catch (err) {
                showAlert(err.message || 'Error al enviar el código', 'error', 'alertBoxRecovery');
                btn.textContent = 'Enviar código';
                btn.disabled    = false;
            }
        });
    }

    // Botón "Ingresar código" después del éxito del paso 1
    const btnGoToCode = document.getElementById('btnGoToCode');
    if (btnGoToCode) {
        btnGoToCode.addEventListener('click', () => {
            mostrarVista('viewCode');
            hideAlert('alertBoxCode');
            // Mostrar el email en el subtítulo para orientar al usuario
            const subtitle = document.getElementById('codeSubtitle');
            if (subtitle && _recoveryEmail) {
                subtitle.textContent = `Escribe el código de 6 dígitos que enviamos a ${_recoveryEmail}.`;
            }
            const codeInput = document.getElementById('verificationCode');
            if (codeInput) codeInput.value = '';
        });
    }

    // ── Paso 2: verificar código ───────────────────────────────────────────
    const codeForm = document.getElementById('codeForm');
    if (codeForm) {
        codeForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const codigo = document.getElementById('verificationCode').value.trim();
            const btn    = document.getElementById('codeBtn');

            if (!/^\d{6}$/.test(codigo)) {
                showAlert('El código debe tener exactamente 6 dígitos numéricos.', 'error', 'alertBoxCode');
                return;
            }

            btn.textContent = 'Verificando...';
            btn.disabled    = true;
            hideAlert('alertBoxCode');

            try {
                const res = await fetch('/api/verificar-codigo/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    credentials: 'include',
                    body: JSON.stringify({ email: _recoveryEmail, codigo }),
                });

                const data = await res.json();

                if (!res.ok) {
                    throw new Error(data.error || 'Código incorrecto o expirado');
                }

                // Código válido → avanzar a la vista de nueva contraseña
                // Guardamos el código en un campo oculto para el paso final
                document.getElementById('_hiddenCode').value  = codigo;
                document.getElementById('_hiddenEmail').value = _recoveryEmail;
                mostrarVista('viewReset');
                hideAlert('alertBoxReset');

            } catch (err) {
                showAlert(err.message || 'Error al verificar el código', 'error', 'alertBoxCode');
                btn.textContent = 'Verificar código';
                btn.disabled    = false;
            }
        });
    }

    // Reenviar código
    const resendLink = document.getElementById('resendCodeLink');
    if (resendLink) {
        resendLink.addEventListener('click', async () => {
            if (!_recoveryEmail) {
                mostrarVista('viewRecovery');
                return;
            }
            resendLink.textContent = 'Reenviando...';
            try {
                await fetch('/api/recuperar-password/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    credentials: 'include',
                    body: JSON.stringify({ email: _recoveryEmail }),
                });
                showAlert('Código reenviado. Revisa tu bandeja de entrada.', 'success', 'alertBoxCode');
            } catch {
                showAlert('No se pudo reenviar el código.', 'error', 'alertBoxCode');
            } finally {
                resendLink.textContent = 'Reenviar código';
            }
        });
    }

    // ── Paso 3: nueva contraseña ───────────────────────────────────────────
    const resetForm = document.getElementById('resetForm');
    if (resetForm) {
        const newPasswordInput  = document.getElementById('newPassword');
        const confirmInput      = document.getElementById('confirmPassword');
        const resetBtn          = document.getElementById('resetBtn');

        // Indicador de fortaleza
        if (newPasswordInput) {
            newPasswordInput.addEventListener('input', () => {
                const pwd = newPasswordInput.value;
                actualizarReglas(pwd);
                actualizarFortaleza(pwd);
                validarFormReset();
            });
        }
        if (confirmInput) {
            confirmInput.addEventListener('input', validarFormReset);
        }

        resetForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const nueva_password = document.getElementById('newPassword').value;
            const confirmar      = document.getElementById('confirmPassword').value;
            const email          = document.getElementById('_hiddenEmail').value;
            const codigo         = document.getElementById('_hiddenCode').value;
            const btn            = document.getElementById('resetBtn');

            if (nueva_password !== confirmar) {
                showAlert('Las contraseñas no coinciden.', 'error', 'alertBoxReset');
                return;
            }

            btn.textContent = 'Restableciendo...';
            btn.disabled    = true;
            hideAlert('alertBoxReset');

            try {
                const res = await fetch('/api/restablecer-password/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    credentials: 'include',
                    body: JSON.stringify({ email, codigo, nueva_password }),
                });

                const data = await res.json();

                if (!res.ok) {
                    throw new Error(data.error || 'No se pudo actualizar la contraseña');
                }

                showAlert('¡Contraseña actualizada! Redirigiendo...', 'success', 'alertBoxReset');
                setTimeout(() => { mostrarVista('viewLogin'); }, 2000);

            } catch (err) {
                showAlert(err.message || 'Error al restablecer la contraseña', 'error', 'alertBoxReset');
                btn.textContent = 'Restablecer contraseña';
                btn.disabled    = false;
            }
        });
    }

    // ── Toggle mostrar/ocultar contraseña ──────────────────────────────────
    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const input    = document.getElementById(targetId);
            if (!input) return;
            input.type = input.type === 'password' ? 'text' : 'password';
        });
    });

});

// ── Helpers de validación de contraseña ───────────────────────────────────────

function actualizarReglas(pwd) {
    const reglas = {
        'rule-length':  pwd.length >= 8,
        'rule-upper':   /[A-Z]/.test(pwd),
        'rule-lower':   /[a-z]/.test(pwd),
        'rule-number':  /\d/.test(pwd),
        'rule-special': /[!@#$%^&*()\-_=+\[\]{};:'",.<>/?\\|`~]/.test(pwd),
    };
    Object.entries(reglas).forEach(([id, ok]) => {
        const el = document.getElementById(id);
        if (el) {
            el.style.color = ok ? '#4ade80' : '#5a7a9f';
        }
    });
}

function actualizarFortaleza(pwd) {
    let score = 0;
    if (pwd.length >= 8)                                               score++;
    if (/[A-Z]/.test(pwd))                                            score++;
    if (/[a-z]/.test(pwd))                                            score++;
    if (/\d/.test(pwd))                                               score++;
    if (/[!@#$%^&*()\-_=+\[\]{};:'",.<>/?\\|`~]/.test(pwd))         score++;

    const fill  = document.getElementById('strengthFill');
    const label = document.getElementById('strengthLabel');
    if (!fill || !label) return;

    const niveles = [
        { pct: '0%',   color: 'transparent', texto: '' },
        { pct: '20%',  color: '#ef4444',     texto: 'Muy débil' },
        { pct: '40%',  color: '#f97316',     texto: 'Débil' },
        { pct: '60%',  color: '#eab308',     texto: 'Regular' },
        { pct: '80%',  color: '#22c55e',     texto: 'Fuerte' },
        { pct: '100%', color: '#4ade80',     texto: 'Muy fuerte' },
    ];
    const n = niveles[score];
    fill.style.width      = n.pct;
    fill.style.background = n.color;
    label.textContent     = n.texto;
    label.style.color     = n.color;
}

function validarFormReset() {
    const pwd     = (document.getElementById('newPassword')     || {}).value || '';
    const confirm = (document.getElementById('confirmPassword') || {}).value || '';
    const btn     = document.getElementById('resetBtn');
    if (!btn) return;

    const valida =
        pwd.length >= 8 &&
        /[A-Z]/.test(pwd) &&
        /[a-z]/.test(pwd) &&
        /\d/.test(pwd) &&
        /[!@#$%^&*()\-_=+\[\]{};:'",.<>/?\\|`~]/.test(pwd) &&
        pwd === confirm;

    btn.disabled = !valida;
}
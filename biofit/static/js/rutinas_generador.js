console.log("rutinas_generador.js cargado v3");
let rutinaActual = null;
let rutinaGuardada = true;
let selectedDaysForSave = [];

function getAuthToken() {
    return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
}

async function cargarContextoGimnasio() {
    const badge = document.getElementById('gym-context-badge');
    const icon = document.getElementById('gym-badge-icon');
    const text = document.getElementById('gym-badge-text');
    if (!badge || !icon || !text) return;

    try {
        const res = await fetch('/inventory/api/gimnasios/contexto/');
        const data = await res.json();
        if (data.gym_id && data.gym_nombre) {
            icon.textContent = '🏋️';
            text.innerHTML = `Rutina adaptada al inventario de — <strong>${data.gym_nombre} </strong> — solo se usarán los equipos disponibles allí.`;
            badge.style.background = 'rgba(42,82,152,0.12)';
            badge.style.borderColor = 'rgba(96,165,250,0.25)';
            badge.style.color = '#93c5fd';
        } else {
            icon.textContent = '🏠';
            text.textContent = 'No tienes un gimnasio asignado — tu rutina usará ejercicios con peso corporal.';
            badge.style.background = 'rgba(180,130,30,0.1)';
            badge.style.borderColor = 'rgba(250,200,80,0.2)';
            badge.style.color = '#fbbf24';
        }
    } catch (_) {
        icon.textContent = '⚠️';
        text.textContent = 'No se pudo verificar tu gimnasio. La rutina se generará con equipamiento general.';
        badge.style.background = 'rgba(239,68,68,0.08)';
        badge.style.borderColor = 'rgba(239,68,68,0.2)';
        badge.style.color = '#fca5a5';
    }
}

function renderEjercicios(lista) {
    if (!Array.isArray(lista) || lista.length === 0) {
        return '<p class="empty-exercises">Sin ejercicios para esta fase.</p>';
    }
    return lista.map(ej => `
        <div class="exercise-card">
            <h4>${ej.ejercicio}</h4>
            <p>
                <strong>🔢 Series:</strong> ${ej.series} &nbsp;|&nbsp;
                <strong>🔁 Reps:</strong> ${ej.repeticiones} &nbsp;|&nbsp;
                <strong>⏱️ Descanso:</strong> ${ej.descanso}
            </p>
            ${ej.nota ? `<p class="exercise-note">💡 <strong>Nota:</strong> ${ej.nota}</p>` : ''}
        </div>
    `).join('');
}

function renderRutina(rutina) {
    const content = document.getElementById('routineContent');
    if (!content) return;
    rutinaActual = rutina;
    rutinaGuardada = false;
    const dias = rutina.dias || [];
    if (dias.length === 0) {
        content.innerHTML = '<p class="empty-exercises">No se generaron días de entrenamiento.</p>';
        return;
    }

    const tabsBtns = dias.map((dia, i) => `
        <button onclick="mostrarDia(${i})" id="tab-btn-${i}" class="tab-button${i === 0 ? ' active' : ''}">
            ${dia.dia}
        </button>
    `).join('');

    const diasHtml = dias.map((dia, i) => `
        <div id="dia-panel-${i}" class="day-panel" style="display:${i === 0 ? 'block' : 'none'};">
            ${dia.enfoque ? `<p class="day-focus">🎯 Enfoque: <strong>${dia.enfoque}</strong></p>` : ''}
            <div class="day-container">
                <h3 class="day-title">🔥 Calentamiento</h3>
                ${renderEjercicios(dia.calentamiento)}
            </div>
            <div class="day-container">
                <h3 class="day-title">💪 Entrenamiento Principal</h3>
                ${renderEjercicios(dia.entrenamiento_principal)}
            </div>
            <div class="day-container">
                <h3 class="day-title">🧘 Estiramiento</h3>
                ${renderEjercicios(dia.estiramiento)}
            </div>
        </div>
    `).join('');

    content.innerHTML = `
        <div class="save-routine-row">
            <button id="btnSave" class="btn-save-routine" onclick="guardarRutina()">💾 Activar y Guardar esta Rutina</button>
        </div>
        <div class="routine-card">
            <div class="tab-bar">${tabsBtns}</div>
            ${diasHtml}
        </div>
    `;
}

function mostrarDia(idx) {
    document.querySelectorAll('[id^="dia-panel-"]').forEach((el, i) => {
        el.style.display = i === idx ? 'block' : 'none';
    });
    document.querySelectorAll('[id^="tab-btn-"]').forEach((btn, i) => {
        btn.classList.toggle('active', i === idx);
    });
}

async function procesarGeneracion(e) {
    console.log("procesarGeneracion llamado");
    e.preventDefault();

    const btn = document.getElementById('btnSubmit');
    const content = document.getElementById('routineContent');
    const levelEl = document.getElementById('level');
    const goalEl = document.getElementById('goal');
    const routinePageEl = document.getElementById('routinePage');
    const csrfTokenEl = document.querySelector('[name=csrfmiddlewaretoken]');

    console.log("Elementos del formulario", { btn, content, levelEl, goalEl, routinePageEl, csrfTokenEl });

    if (!btn) { console.error("Falta btnSubmit"); return; }
    if (!content) { console.error("Falta routineContent"); return; }
    if (!levelEl) { console.error("Falta level"); return; }
    if (!goalEl) { console.error("Falta goal"); return; }
    if (!routinePageEl) { console.error("Falta routinePage"); return; }
    if (!csrfTokenEl) { console.error("Falta csrfmiddlewaretoken"); return; }

    const level = levelEl.value;
    const goal = goalEl.value;
    const selectedDays = Array.from(document.querySelectorAll('input[name="day"]:checked')).map(cb => cb.value);
    selectedDaysForSave = selectedDays;
    
    if (selectedDays.length === 0) {
        alert('Por favor, selecciona al menos un día de entrenamiento.');
        return;
    }
    const days = selectedDays.length;

    btn.textContent = '🧠 Pensando tu rutina ideal...';
    btn.disabled = true;
    content.innerHTML = `
        <div class="loading-state">
            <p>Generando tu estructura de entrenamiento de forma inteligente, por favor espera...</p>
        </div>
    `;

    try {
        const token = getAuthToken();
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfTokenEl.value
        };
        if (token) {
            headers['Authorization'] = 'Bearer ' + token;
        }

        console.log("Enviando datos", { nivel: level, objetivo: goal, dias: days, nombres_dias: selectedDays });

        const response = await fetch(routinePageEl.dataset.generateUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({ nivel: level, objetivo: goal, dias: days, nombres_dias: selectedDays })
    });

        console.log("Respuesta del servidor", response.status);
        const data = await response.json();
        console.log("Datos recibidos", data);

        if (response.ok && data.rutina) {
            rutinaActual = data.rutina;
            renderRutina(data.rutina);
        } else {
            content.innerHTML = `
                <div class="error-card">
                    <strong>Error del servidor:</strong> ${data.error || 'No se recibió un objeto de rutina válido.'}
                </div>
            `;
        }
    } catch (err) {
        console.error(err);
        content.innerHTML = `
            <div class="error-card">
                ⚠️ Ocurrió un problema de red al procesar o renderizar los datos de tu rutina.
            </div>
        `;
    } finally {
        btn.textContent = '✨ Generar Mi Plan Personalizado';
        btn.disabled = false;
    }
}

function guardarRutina() {
    if (!rutinaActual) return;
    const page = document.getElementById('routinePage');
    if (!page) return;

    const usuarioAutenticado = page.dataset.userAuthenticated === 'true';
    const saveUrl = page.dataset.saveUrl;
    const loginUrl = page.dataset.loginUrl;
    const detailUrl = page.dataset.detailUrl;
    const btn = document.getElementById('btnSave');
    const levelEl = document.getElementById('level');
    const goalEl = document.getElementById('goal');
    const csrfTokenEl = document.querySelector('[name=csrfmiddlewaretoken]');

    if (!usuarioAutenticado) {
        alert('Para guardar tu plan necesitas estar identificado.');
        window.location.href = loginUrl;
        return;
    }
    if (!btn || !levelEl || !goalEl || !csrfTokenEl) {
        console.error('Faltan elementos para guardar la rutina', { btn, levelEl, goalEl, csrfTokenEl });
        return;
    }

    btn.textContent = '💾 Guardando en tu perfil...';
    btn.disabled = true;

    const level = levelEl.value;
    const goal = goalEl.value;
    const days = rutinaActual.dias ? rutinaActual.dias.length : 0;

    fetch(saveUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfTokenEl.value,
        },
        body: JSON.stringify({ rutina: rutinaActual, inputs: { nivel: level, objetivo: goal, dias: days, nombres_dias: selectedDaysForSave } })
    })
    .then(res => res.json().then(data => ({ ok: res.ok, data })))
    .then(({ ok, data }) => {
        if (ok && data.success) {
            rutinaGuardada = true;
            alert('¡Plan guardado con éxito! Redirigiendo al detalle de tu rutina...');
            window.location.href = detailUrl;
        } else {
            alert('No se pudo guardar la rutina: ' + (data.error || 'Sesión inválida'));
        }
    })
    .catch(err => {
        alert('Error de red al intentar conectar con la base de datos.');
        console.error(err);
    })
    .finally(() => {
        btn.textContent = '💾 Activar y Guardar esta Rutina';
        btn.disabled = false;
    });
}

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM completamente cargado");
    const routineForm = document.getElementById('routineForm');
    if (routineForm) {
        console.log("Formulario encontrado, agregando event listener");
        routineForm.addEventListener('submit', procesarGeneracion);
    } else {
        console.error("No se encontró el formulario con ID routineForm");
    }
    cargarContextoGimnasio();
});

window.addEventListener('beforeunload', (e) => {
    if (rutinaActual && !rutinaGuardada) {
        e.preventDefault();
        e.returnValue = 'Tienes una rutina sin guardar. ¿Seguro que quieres salir?';
        return e.returnValue;
    }
});

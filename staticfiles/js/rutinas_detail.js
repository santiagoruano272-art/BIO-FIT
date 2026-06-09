let _pendingRoutineId = null;
let _pendingCardIndex = null;
let _toastTimer = null;

function getCsrf() {
    return document.cookie.split(';')
        .map(c => c.trim())
        .find(c => c.startsWith('csrftoken='))
        ?.split('=')[1] || '';
}

function mostrarToast(msg, tipo = 'success') {
    const el = document.getElementById('toast-biofit');
    if (!el) return;
    const iconos = { success: '✅', error: '❌' };
    el.textContent = `${iconos[tipo] || '•'} ${msg}`;
    el.className = `toast-biofit ${tipo} show`;
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(() => { el.classList.remove('show'); }, 3500);
}

function mostrarDia(routineId, diaIdx, btnEl) {
    document.querySelectorAll(`[id^="${routineId}-dia-"]`).forEach(p => p.classList.remove('active'));
    btnEl.closest('.routine-container-card')
         .querySelectorAll('.day-tab-btn')
         .forEach(b => b.classList.remove('active'));
    const panel = document.getElementById(`${routineId}-dia-${diaIdx}`);
    if (panel) panel.classList.add('active');
    btnEl.classList.add('active');
}

function solicitarEliminar(routineId, cardIndex) {
    _pendingRoutineId = routineId;
    _pendingCardIndex = cardIndex;
    const modal = document.getElementById('modal-eliminar');
    if (modal) modal.classList.add('active');
}

function cerrarModal() {
    const modal = document.getElementById('modal-eliminar');
    if (modal) modal.classList.remove('active');
    _pendingRoutineId = null;
    _pendingCardIndex = null;
}

async function confirmarEliminar() {
    if (!_pendingRoutineId) return;

    const routineId = _pendingRoutineId;
    const cardIndex = _pendingCardIndex;
    const btnConfirm = document.getElementById('btn-modal-confirm');
    if (!btnConfirm) return;

    btnConfirm.disabled = true;
    btnConfirm.textContent = '⏳ Eliminando…';

    cerrarModal();

    try {
        const resp = await fetch(`/rutinas/api/eliminar/${routineId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrf(),
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
        });

        const data = await resp.json().catch(() => ({}));

        if (!resp.ok) {
            throw new Error(data.error || `Error ${resp.status}`);
        }

        const card = document.getElementById(`card-rutina-${cardIndex}`);
        if (card) {
            card.classList.add('removing');
            setTimeout(() => {
                card.remove();
                _verificarVacio();
            }, 380);
        }

        mostrarToast('Rutina eliminada correctamente.', 'success');
    } catch (err) {
        console.error('[BIO-FIT] Error eliminando rutina:', err);
        mostrarToast(`No se pudo eliminar: ${err.message}`, 'error');
    } finally {
        btnConfirm.disabled = false;
        btnConfirm.innerHTML = '🗑️ Sí, eliminar';
    }
}

function _verificarVacio() {
    const cards = document.querySelectorAll('.routine-container-card');
    if (cards.length === 0) {
        const empty = document.getElementById('empty-state-js');
        const actions = document.getElementById('actions-area');
        if (empty) empty.classList.add('visible');
        if (actions) actions.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('modal-eliminar');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) cerrarModal();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') cerrarModal();
    });
});
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

const csrfToken = getCookie('csrftoken');

function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }
function showSpinner() { document.getElementById('loadingSpinner').style.display = 'block'; }
function hideSpinner() { document.getElementById('loadingSpinner').style.display = 'none'; }
function showError(elementId, text) {
    const err = document.getElementById(elementId);
    if (!err) return;
    err.textContent = text;
    err.style.display = 'block';
}

function openEditModal(id, nombre, tipo, ubicacion, fecha, estado) {
    document.getElementById('edit_id').value = id;
    document.getElementById('edit_nombre').value = nombre;
    document.getElementById('edit_tipo').value = tipo;
    document.getElementById('edit_ubicacion').value = ubicacion;
    document.getElementById('edit_estado').value = estado;
    if (fecha) {
        try {
            const d = new Date(fecha);
            if (!isNaN(d.getTime())) document.getElementById('edit_fecha').value = d.toISOString().split('T')[0];
        } catch (error) {
            console.warn('Fecha inválida:', error);
        }
    }
    openModal('editModal');
}

async function deleteEquipo(id) {
    if (!confirm('¿Confirmas la eliminación permanente de este activo?')) return;
    showSpinner();
    try {
        const res = await fetch(`/inventory/api/equipos/${id}/eliminar/`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': csrfToken }
        });
        const data = await res.json();
        hideSpinner();
        if (res.ok && data.success) {
            window.location.reload();
        } else {
            alert(data.error || 'Fallo al eliminar registro.');
        }
    } catch (err) {
        hideSpinner();
        alert('Fallo de red al solicitar eliminación.');
        console.error(err);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const addForm = document.getElementById('addForm');
    if (addForm) {
        addForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            showSpinner();
            const payload = {
                nombre: document.getElementById('add_nombre').value,
                tipo: document.getElementById('add_tipo').value,
                ubicacion: document.getElementById('add_ubicacion').value,
                fecha_adquisicion: document.getElementById('add_fecha').value,
                estado: document.getElementById('add_estado').value
            };
            try {
                const res = await fetch("/inventory/api/equipos/", {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                hideSpinner();
                if (res.ok && data.success) window.location.reload();
                else showError('addError', data.error || 'Error al persistir el registro.');
            } catch (err) {
                hideSpinner();
                showError('addError', 'Error crítico de red.');
            }
        });
    }

    const editForm = document.getElementById('editForm');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            showSpinner();
            const id = document.getElementById('edit_id').value;
            const payload = {
                nombre: document.getElementById('edit_nombre').value,
                tipo: document.getElementById('edit_tipo').value,
                ubicacion: document.getElementById('edit_ubicacion').value,
                fecha_adquisicion: document.getElementById('edit_fecha').value,
                estado: document.getElementById('edit_estado').value
            };
            try {
                const res = await fetch(`/inventory/api/equipos/${id}/`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                hideSpinner();
                if (res.ok && data.success) window.location.reload();
                else showError('editError', data.error || 'Error al actualizar el registro.');
            } catch (err) {
                hideSpinner();
                showError('editError', 'Error de red en actualización.');
            }
        });
    }
});
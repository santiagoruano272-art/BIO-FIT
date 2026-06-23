const API = {
    perfil:    '/api/perfil/',
    gimnasio:  '/api/perfil/gimnasio/',
    gimnasios: (q) => `/api/gimnasios/?q=${encodeURIComponent(q)}`,
};

const $ = id => document.getElementById(id);
const token = () => localStorage.getItem('biofit_token') || '';
const getCsrf = () => (
    document.cookie.split(';')
        .map(c => c.trim())
        .find(c => c.startsWith('csrftoken='))
        ?.split('=')[1] || ''
);

function showLoading(v) { $('loading-overlay').classList.toggle('active', v); }

function toast(msg, type = 'success') {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${type === 'success' ? '✅' : '❌'}</span> ${msg}`;
    $('toast-container').appendChild(el);
    setTimeout(() => el.remove(), 3500);
}

let perfil = {};
let gimSeleccionado = null;
let todasLasSedes = [];

async function cargarPerfil() {
    console.log("🔄 Cargando perfil...");
    showLoading(true);
    try {
        const r = await fetch(API.perfil, {
            credentials: 'include',
        });

        if (r.status === 401) {
            window.location.href = '/login/?next=/perfil/';
            return;
        }

        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        perfil = await r.json();
        console.log("✅ Perfil cargado desde servidor:", perfil);

    } catch (err) {
        console.warn("cargarPerfil: usando caché local —", err.message);
        perfil = {
            nombre:        localStorage.getItem('biofit_nombre')        || '',
            sobrenombre:   localStorage.getItem('biofit_sobrenombre')   || '',
            avatar_url:    localStorage.getItem('biofit_avatar_url')    || '',
            email:         localStorage.getItem('biofit_email')         || '',
            telefono:      localStorage.getItem('biofit_tel')           || '',
            nivel:         localStorage.getItem('biofit_nivel')         || 'principiante',
            rol:           localStorage.getItem('biofit_rol')           || 'atleta',
            gym_id:        localStorage.getItem('biofit_gym_id')        || null,
            gym_nombre:    localStorage.getItem('biofit_gym_nombre')    || null,
            gym_ubicacion: localStorage.getItem('biofit_gym_ubicacion') || null,
            _sesionRota:   true,
        };
        console.log("ℹ️ Perfil cargado desde caché:", perfil);
    } finally {
        showLoading(false);
    }
    renderPerfil();
}

function renderPerfil() {
    console.log("🎨 Renderizando perfil con datos:", perfil);
    const nombre = perfil.nombre || '';
    const iniciales = nombre.trim().split(' ')
        .slice(0, 2).map(p => (p[0] || '').toUpperCase()).join('') || '?';

    const avatarImg = $('avatar-img');
    const avatarInitials = $('avatar-initials');
    console.log("🖼️ avatar_url encontrado:", perfil.avatar_url ? "SI" : "NO");
    
    if (perfil.avatar_url) {
        console.log("📷 Mostrando imagen desde:", perfil.avatar_url.substring(0, 50) + "...");
        avatarImg.src = perfil.avatar_url;
        avatarImg.style.display = 'block';
        avatarInitials.style.display = 'none';
    } else {
        console.log("❌ No hay avatar_url, mostrando iniciales");
        avatarImg.style.display = 'none';
        avatarInitials.style.display = 'block';
        avatarInitials.textContent = iniciales;
    }
    
    $('avatar-name').textContent     = perfil.sobrenombre || nombre || 'Atleta';
    $('avatar-email').textContent    = perfil.email || '–';
    $('badge-rol').textContent       = perfil.rol || 'atleta';
    $('field-nombre').value          = perfil.nombre   || '';
    $('field-sobrenombre').value     = perfil.sobrenombre || '';
    $('field-email').value           = perfil.email    || '';
    $('field-telefono').value        = perfil.telefono || '';
    $('field-nivel').value           = perfil.nivel    || 'principiante';

    renderGym();
}

function renderGym() {
    const linked   = $('gym-linked-view');
    const unlinked = $('gym-unlinked-view');
    const notFound = $('gym-not-found');

    linked.style.display   = 'none';
    unlinked.style.display = 'none';
    notFound.classList.remove('active');
    $('confirm-desvincular').classList.remove('active');

    if (perfil.gym_id) {
        const esHuerfano = perfil.gym_nombre &&
            perfil.gym_nombre.startsWith('Gimnasio no encontrado');

        if (esHuerfano) {
            notFound.classList.add('active');
        } else {
            linked.style.display = 'block';
            $('gym-nombre').textContent    = perfil.gym_nombre   || perfil.gym_id;
            $('gym-ubicacion').textContent = perfil.gym_ubicacion || '–';
        }
    } else {
        unlinked.style.display = 'block';
    }
}

$('form-perfil').addEventListener('submit', async (e) => {
    e.preventDefault();
    console.log("📝 Enviando formulario...");
    const btn = $('btn-guardar');
    const nombre = $('field-nombre').value.trim();
    const sobrenombre = $('field-sobrenombre').value.trim();
    const email  = $('field-email').value.trim();
    const tel    = $('field-telefono').value.trim();
    const nivel  = $('field-nivel').value;

    if (!nombre) {
        toast('El nombre no puede estar vacío.', 'error');
        return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        toast('Correo electrónico no válido.', 'error');
        return;
    }

    if (perfil._sesionRota) {
        toast('Tu sesión expiró. Recarga la página o inicia sesión de nuevo.', 'error');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span> Guardando…';

    const body = { nombre, sobrenombre, email, telefono: tel, nivel };
    if (perfil.avatar_url) {
        body.avatar_url = perfil.avatar_url;
    }
    console.log("📤 Body a enviar:", Object.assign({}, body, { avatar_url: body.avatar_url ? "BASE64 (oculto)" : "NO" }));

    try {
        const r = await fetch(API.perfil, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken':  getCsrf(),
            },
            credentials: 'include',
            body: JSON.stringify(body),
        });
        if (!r.ok) {
            const err = await r.json().catch(() => ({}));
            throw new Error(err.error || r.status);
        }
        const responseData = await r.json();
        console.log("✅ Respuesta del servidor:", responseData);
        
        Object.assign(perfil, responseData);
        localStorage.setItem('biofit_nombre', responseData.nombre);
        localStorage.setItem('biofit_sobrenombre', responseData.sobrenombre);
        localStorage.setItem('biofit_avatar_url', responseData.avatar_url || '');
        localStorage.setItem('biofit_email', responseData.email);
        localStorage.setItem('biofit_tel', responseData.telefono);
        localStorage.setItem('biofit_nivel', responseData.nivel);
        
        renderPerfil();
        toast('Perfil actualizado correctamente.');
    } catch (err) {
        toast(`Error al guardar: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>💾</span> Guardar cambios';
    }
});

$('btn-desvincular').addEventListener('click', () => {
    $('confirm-desvincular').classList.add('active');
});
$('btn-confirm-cancel').addEventListener('click', () => {
    $('confirm-desvincular').classList.remove('active');
});
$('btn-confirm-ok').addEventListener('click', async () => {
    showLoading(true);
    try {
        const r = await fetch(API.gimnasio, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrf(),
            },
            credentials: 'include',
        });
        if (!r.ok) {
            const err = await r.json().catch(() => ({}));
            throw new Error(err.error || r.status);
        }
        perfil.gym_id = null; perfil.gym_nombre = null; perfil.gym_ubicacion = null;
        localStorage.removeItem('biofit_gym_id');
        localStorage.removeItem('biofit_gym_nombre');
        localStorage.removeItem('biofit_gym_ubicacion');
        renderGym();
        toast('Te desvinculaste del gimnasio correctamente.');
    } catch (err) {
        toast(`Error al desvincular: ${err.message}`, 'error');
    } finally {
        showLoading(false);
    }
});

function abrirModal() {
    gimSeleccionado = null;
    $('btn-confirmar-vinculacion').disabled = true;
    $('gym-search-input').value = '';
    $('modal-error-banner').classList.remove('active');
    $('modal-gimnasio').classList.add('active');
    if (todasLasSedes.length > 0) {
        renderGymList(todasLasSedes);
    } else {
        cargarSedes('');
    }
    setTimeout(() => $('gym-search-input').focus(), 150);
}
function cerrarModal() {
    $('modal-gimnasio').classList.remove('active');
}

$('btn-vincular').addEventListener('click', abrirModal);
$('btn-vincular-desde-error').addEventListener('click', abrirModal);
$('btn-cambiar-gym').addEventListener('click', abrirModal);
$('modal-close-btn').addEventListener('click', cerrarModal);
$('modal-cancel-btn').addEventListener('click', cerrarModal);
$('modal-gimnasio').addEventListener('click', e => {
    if (e.target === $('modal-gimnasio')) cerrarModal();
});

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') cerrarModal();
});

let searchDebounce;
$('gym-search-input').addEventListener('input', () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
        cargarSedes($('gym-search-input').value.trim());
    }, 300);
});

async function cargarSedes(q) {
    $('gym-list').innerHTML = '<li style="padding:20px;text-align:center;color:var(--text-muted);">Buscando sedes…</li>';
    $('gym-empty').style.display = 'none';
    $('modal-error-banner').classList.remove('active');

    try {
        const r = await fetch(API.gimnasios(q), {
            credentials: 'include',
        });
        const data = await r.json();

        if (!r.ok) {
            $('modal-error-banner').textContent =
                data.error || 'No se pudo conectar con Firestore. Intenta más tarde.';
            $('modal-error-banner').classList.add('active');
            $('gym-list').innerHTML = '';
            return;
        }

        todasLasSedes = Array.isArray(data) ? data : [];
        renderGymList(todasLasSedes);

    } catch {
        $('modal-error-banner').textContent =
            'Error de red al consultar las sedes. Verifica tu conexión.';
        $('modal-error-banner').classList.add('active');
        $('gym-list').innerHTML = '';
    }
}

function renderGymList(lista) {
    const ul    = $('gym-list');
    const empty = $('gym-empty');
    ul.innerHTML = '';

    if (!lista.length) {
        empty.style.display = 'block';
        return;
    }
    empty.style.display = 'none';

    ul._gymMap = {};
    lista.forEach(g => {
        const li = document.createElement('li');
        li.className = 'gym-list-item' + (gimSeleccionado?.id === g.id ? ' selected' : '');
        li.setAttribute('role', 'option');
        li.dataset.id = g.id;
        li.innerHTML = `
            <div class="gym-dot" style="pointer-events:none">🏢</div>
            <div style="pointer-events:none">
                <h4>${g.nombre}</h4>
                <span>${g.ubicacion || 'Sin ubicación registrada'}</span>
            </div>
            <span class="check" style="pointer-events:none" aria-hidden="true">✓</span>
        `;
        ul._gymMap[g.id] = { gym: g, el: li };
        ul.appendChild(li);
    });
    ul.onclick = (e) => {
        const li = e.target.closest('.gym-list-item');
        if (!li) return;
        const entry = ul._gymMap[li.dataset.id];
        if (entry) seleccionarGym(entry.gym, entry.el);
    };
}

function seleccionarGym(gym, el) {
    document.querySelectorAll('.gym-list-item').forEach(i => i.classList.remove('selected'));
    el.classList.add('selected');
    gimSeleccionado = gym;
    $('btn-confirmar-vinculacion').disabled = false;
}

$('btn-confirmar-vinculacion').addEventListener('click', async () => {
    if (!gimSeleccionado) return;

    if (perfil._sesionRota) {
        toast('Tu sesión expiró. Redirigiendo al login…', 'error');
        cerrarModal();
        setTimeout(() => { window.location.href = '/login/?next=/perfil/'; }, 1500);
        return;
    }

    cerrarModal();
    showLoading(true);
    try {
        const r = await fetch(API.gimnasio, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken':  getCsrf(),
            },
            credentials: 'include',
            body: JSON.stringify({ gym_id: gimSeleccionado.id }),
        });
        const data = await r.json();

        if (!r.ok) {
            if (r.status === 401) {
                toast('Sesión expirada. Redirigiendo al login…', 'error');
                setTimeout(() => { window.location.href = '/login/?next=/perfil/'; }, 1500);
                return;
            }
            toast(data.error || 'Error al vincular el gimnasio.', 'error');
            return;
        }

        perfil.gym_id        = data.gym_id;
        perfil.gym_nombre    = data.gym_nombre;
        perfil.gym_ubicacion = data.gym_ubicacion || gimSeleccionado.ubicacion || '';

        localStorage.setItem('biofit_gym_id',        perfil.gym_id);
        localStorage.setItem('biofit_gym_nombre',    perfil.gym_nombre);
        localStorage.setItem('biofit_gym_ubicacion', perfil.gym_ubicacion);

        renderGym();
        toast(`Vinculado a "${perfil.gym_nombre}" ✅`);

    } catch (err) {
        toast('Error de red al vincular. Intenta de nuevo.', 'error');
    } finally {
        showLoading(false);
    }
});

/* ── Avatar Upload Handler ── */
document.addEventListener('DOMContentLoaded', function() {
    console.log("🎯 DOM listo para perfil.js");
    
    const avatarInput = document.getElementById('field-avatar');
    if (avatarInput) {
        avatarInput.addEventListener('change', async function(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            console.log("📷 Archivo seleccionado para avatar:", file.name);
            
            // Preview the image immediately
            const reader = new FileReader();
            reader.onload = function(event) {
                console.log("✅ Imagen leída, mostrando preview...");
                const avatarImg = document.getElementById('avatar-img');
                const avatarInitials = document.getElementById('avatar-initials');
                if (avatarImg && avatarInitials) {
                    avatarImg.src = event.target.result;
                    avatarImg.style.display = 'block';
                    avatarInitials.style.display = 'none';
                }
                
                // Option 1: Save as base64
                perfil.avatar_url = event.target.result;
                localStorage.setItem('biofit_avatar_url', event.target.result);
                toast("Vista previa de avatar actualizada! Guarda cambios para aplicar.", "success");
            };
            reader.readAsDataURL(file);
        });
    }
    
    cargarPerfil();
});

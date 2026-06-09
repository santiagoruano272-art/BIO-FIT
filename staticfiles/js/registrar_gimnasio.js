function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('form-gym');
    const msgDiv = document.getElementById('msg');
    if (!form || !msgDiv) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        msgDiv.style.display = 'none';

        const endpoint = form.dataset.endpoint;
        const payload = {
            nombre: document.getElementById('gym-name').value,
            ubicacion: document.getElementById('gym-location').value,
            telefono: document.getElementById('gym-phone').value
        };

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(payload)
            });
            const data = await response.json();

            if (response.ok && data.success) {
                msgDiv.style.color = '#27ae60';
                msgDiv.textContent = `¡Gimnasio creado con ID: ${data.gym_id}! Subcolección de equipamientos inicializada.`;
                msgDiv.style.display = 'block';
                form.reset();
            } else {
                msgDiv.style.color = '#c0392b';
                msgDiv.textContent = data.error || 'Fallo en la persistencia del documento.';
                msgDiv.style.display = 'block';
            }
        } catch (err) {
            msgDiv.style.color = '#c0392b';
            msgDiv.textContent = 'Error fatal de conexión con los endpoints.';
            msgDiv.style.display = 'block';
        }
    });
});
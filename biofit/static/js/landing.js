document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('biofit_token');

    if (!token) {
        window.location.href = '/login/';
        return;
    }

    const nombre  = localStorage.getItem('biofit_nombre');
    const email   = localStorage.getItem('biofit_email');
    const display = document.getElementById('user-display-name');
    if (display) {
        if (nombre && nombre.trim()) {
            display.textContent = nombre.trim().split(' ')[0];
        } else if (email) {
            display.textContent = email.split('@')[0];
        }
    }

    const nivel     = localStorage.getItem('biofit_nivel');
    const levelEl   = document.getElementById('user-level');
    if (nivel && levelEl) {
        const nivelMap = {
            'principiante': 'Principiante',
            'intermedio':   'Intermedio',
            'avanzado':     'Avanzado',
        };
        levelEl.textContent = nivelMap[nivel.toLowerCase()] || nivel;
    }

    const appRoot = document.getElementById('biofit-app-root');
    const currentServerRole = appRoot ? appRoot.getAttribute('data-role') : 'atleta';
    const localBrowserRole  = localStorage.getItem('biofit_rol');

    if (localBrowserRole === 'admin' && currentServerRole !== 'admin') {
        console.log('[BIO-FIT] Sincronizando rol → panel de administración...');
        window.location.href = '/inventory/dashboard/';
    }

    const dayButtons = document.querySelectorAll('.day-btn');
    dayButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            dayButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });

    const trainingDaysContainer = document.getElementById('trainingDays');
    if (trainingDaysContainer) {
        const daysOfWeek = ['DOM', 'LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB'];
        const today = new Date();
        trainingDaysContainer.innerHTML = '';
        for (let i = 0; i < 7; i++) {
            const currentDate = new Date(today);
            currentDate.setDate(today.getDate() + i);
            const dayName = daysOfWeek[currentDate.getDay()];
            const dayNumber = currentDate.getDate();
            const year = currentDate.getFullYear();
            const month = String(currentDate.getMonth() + 1).padStart(2, '0');
            const day = String(dayNumber).padStart(2, '0');
            const dateStr = `${year}-${month}-${day}`;
            const button = document.createElement('button');
            button.className = 'day-btn' + (i === 0 ? ' active' : '');
            button.innerHTML = `${dayName}<br><span style="font-size:0.9rem;">${dayNumber}</span>`;
            button.dataset.date = dateStr;
            button.addEventListener('click', async function() {
                document.querySelectorAll('.day-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                await loadRoutineForDate(this.dataset.date);
            });
            trainingDaysContainer.appendChild(button);
        }
        const today_date = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
        loadRoutineForDate(today_date);
    }

    async function loadRoutineForDate(dateStr) {
        try {
            const response = await fetch(`/rutinas/api/dia/?date=${dateStr}`);
            const data = await response.json();
            if (data.status === 'success') {
                const caloriesEl = document.getElementById('metric-calories');
                if (caloriesEl) {
                    const valueEl = caloriesEl.querySelector('.value');
                    valueEl.textContent = `${data.calorias} kcal`;
                    valueEl.style.animation = 'none';
                    setTimeout(() => { valueEl.style.animation = 'fadeIn 0.5s ease-in'; }, 10);
                }
                const timeEl = document.getElementById('metric-time');
                if (timeEl) {
                    const valueEl = timeEl.querySelector('.value');
                    const tiempoEntero = Number.isFinite(Number(data.tiempo)) ? Math.floor(Number(data.tiempo)) : data.tiempo;
                    valueEl.textContent = `${tiempoEntero} min`;
                    valueEl.style.animation = 'none';
                    setTimeout(() => { valueEl.style.animation = 'fadeIn 0.5s ease-in'; }, 10);
                }
                const bodyInfo = document.querySelector('.body-info strong');
                if (bodyInfo) {
                    bodyInfo.textContent = data.musculos || 'Sin datos';
                    bodyInfo.style.animation = 'none';
                    setTimeout(() => { bodyInfo.style.animation = 'fadeIn 0.5s ease-in'; }, 10);
                    const regions = data.muscle_regions || data.muscleRegions || [];
                    updateBodyHighlights(regions);
                }
                console.log('[BIO-FIT] Rutina cargada para:', dateStr, data);
            } else {
                console.log('[BIO-FIT] Sin rutina para esta fecha:', data.message);
                const caloriesEl = document.getElementById('metric-calories');
                if (caloriesEl) caloriesEl.querySelector('.value').textContent = '0 kcal';
                const timeEl = document.getElementById('metric-time');
                if (timeEl) timeEl.querySelector('.value').textContent = '0 min';
                updateBodyHighlights([]);
            }
        } catch (error) {
            console.error('[BIO-FIT] Error cargando rutina:', error);
        }
    }

    function updateBodyHighlights(regions) {
        const known = ['chest','back','biceps','triceps','shoulders','abs','core','glutes','quads','calves','full_body'];
        known.forEach(r => { const el = document.getElementById(r); if (el) el.classList.remove('highlight'); });
        if (!regions || !regions.length) return;
        if (regions.includes('full_body')) { known.forEach(r => { const el = document.getElementById(r); if (el) el.classList.add('highlight'); }); return; }
        regions.forEach(r => { try { const el = document.getElementById(r); if (el) el.classList.add('highlight'); } catch (e) {} });
    }
    const style = document.createElement('style');
    style.textContent = `@keyframes fadeIn { from { opacity: 0.6; } to { opacity: 1; } }`;
    document.head.appendChild(style);
});
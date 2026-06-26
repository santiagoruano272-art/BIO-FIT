console.log("🚀 BIO-FIT LANDING JS Cargado v8!");

document.addEventListener('DOMContentLoaded', async function() {
    console.log("✅ DOM Listo!");
    
    // Cargar perfil del usuario para mostrar el nombre correcto
    await cargarPerfil();
    
    // Inicializar el calendario y datos del día
    await inicializarCalendario();
    
    // Configurar botones de cambio de vista del cuerpo
    configurarBotonesVistaCuerpo();
});

async function cargarPerfil() {
    try {
        const response = await fetch('/api/perfil/', { credentials: 'include' });
        if (response.ok) {
            const perfil = await response.json();
            console.log("📋 Perfil cargado:", perfil);
            
            // FIX: el nombre ya llega correcto desde el servidor en el render
            // inicial (views.py resuelve sobrenombre/nombre antes de pintar
            // landing.html), así que aquí ya NO hace falta "rellenar" el
            // nombre por defecto. Esto solo sincroniza si el perfil trae un
            // valor real distinto al que ya se mostró (ej. el usuario cambió
            // su apodo en otra pestaña). Nunca lo pisa con 'Atleta'.
            const nombreDisplay = document.getElementById('user-display-name');
            const nombrePerfil = perfil.sobrenombre || perfil.nombre;
            if (nombreDisplay && nombrePerfil && nombreDisplay.textContent !== nombrePerfil) {
                nombreDisplay.textContent = nombrePerfil;
            }
            
            // Actualizar el nivel
            const nivelDisplay = document.getElementById('user-level');
            if (nivelDisplay && perfil.nivel) {
                const nivelCapitalizado = perfil.nivel.charAt(0).toUpperCase() + perfil.nivel.slice(1);
                nivelDisplay.textContent = nivelCapitalizado;
            }
        }
    } catch (error) {
        console.warn("⚠️ No se pudo cargar el perfil:", error);
    }
}

async function inicializarCalendario() {
    const contenedorDias = document.getElementById('trainingDays');
    if (!contenedorDias) return;

    const hoy = new Date();
    const hoyStr = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}-${String(hoy.getDate()).padStart(2, '0')}`;

    // Cargar la rutina de hoy para obtener los días seleccionados
    let diasSeleccionados = ['Lunes', 'Miércoles', 'Viernes']; // Default
    let datosRutina = null;

    try {
        const responseRutina = await fetch(`/rutinas/api/dia/?date=${hoyStr}`, { credentials: 'include' });
        if (responseRutina.ok) {
            datosRutina = await responseRutina.json();
            console.log("📅 Datos de la rutina:", datosRutina);
            
            if (datosRutina.nombres_dias && datosRutina.nombres_dias.length > 0) {
                diasSeleccionados = datosRutina.nombres_dias;
            }
        }
    } catch (error) {
        console.warn("⚠️ No se pudo cargar la rutina inicial:", error);
    }

    // Generar los días del calendario
    await regenerarCalendario(contenedorDias, diasSeleccionados, hoyStr);
    
    // Cargar los datos del primer día (hoy o el próximo día disponible)
    if (datosRutina) {
        await cargarDatosDelDia(hoyStr);
    }
}

async function regenerarCalendario(contenedor, nombresDias, fechaInicial) {
    contenedor.innerHTML = '';

    const diasDeLaSemana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
    const etiquetasCortas = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
    const fechaBase = new Date(fechaInicial || new Date());
    let botonesCreados = 0;
    let primeraFecha = null;
    const maxDias = Math.min(nombresDias.length, 5); // Máximo 5 días o los que haya

    console.log("📆 Generando calendario con días:", nombresDias);

    for (let i = 0; i < 60 && botonesCreados < maxDias; i++) {
        const fecha = new Date(fechaBase);
        fecha.setDate(fechaBase.getDate() + i);
        
        const indiceDiaSemana = fecha.getDay();
        const nombreDiaCompleto = diasDeLaSemana[(indiceDiaSemana + 6) % 7];

        if (nombresDias.includes(nombreDiaCompleto)) {
            const indiceEtiqueta = (indiceDiaSemana + 6) % 7;
            const etiqueta = etiquetasCortas[indiceEtiqueta];
            const numeroDia = fecha.getDate();
            const fechaStr = `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, '0')}-${String(numeroDia).padStart(2, '0')}`;

            const boton = document.createElement('button');
            boton.className = 'day-btn' + (botonesCreados === 0 ? ' active' : '');
            boton.innerHTML = `${etiqueta}<br><span style="font-size:0.9rem">${numeroDia}</span>`;
            boton.dataset.fecha = fechaStr;

            boton.addEventListener('click', async function() {
                // Desmarcar todos los botones
                document.querySelectorAll('.day-btn').forEach(b => b.classList.remove('active'));
                // Marcar el botón clickeado
                this.classList.add('active');
                // Cargar datos del día
                await cargarDatosDelDia(this.dataset.fecha);
            });

            contenedor.appendChild(boton);

            if (botonesCreados === 0) {
                primeraFecha = fechaStr;
            }
            botonesCreados++;
        }
    }

    console.log(`✅ Calendario generado con ${botonesCreados} días`);
}

async function cargarDatosDelDia(fechaStr) {
    console.log("📥 Cargando datos para fecha:", fechaStr);

    try {
        const response = await fetch(`/rutinas/api/dia/?date=${fechaStr}`, { credentials: 'include' });
        const datos = await response.json();
        console.log("📊 Datos del día:", datos);

        // Actualizar calorías
        const elCalorias = document.getElementById('metric-calories');
        if (elCalorias) {
            const valorCalorias = elCalorias.querySelector('.value');
            valorCalorias.textContent = `${datos.calorias || 0} kcal`;
        }

        // Actualizar tiempo
        const elTiempo = document.getElementById('metric-time');
        if (elTiempo) {
            const valorTiempo = elTiempo.querySelector('.value');
            const tiempoEntero = Math.floor(datos.tiempo || 0);
            valorTiempo.textContent = `${tiempoEntero} min`;
        }

        // Actualizar músculos en texto
        const elInfoCuerpo = document.querySelector('.body-info strong');
        if (elInfoCuerpo) {
            elInfoCuerpo.textContent = datos.musculos || 'Sin datos';
        }

        // Actualizar resaltado en el cuerpo
        actualizarResaltadoMusculos(datos.muscle_regions || []);
    } catch (error) {
        console.error("❌ Error al cargar datos del día:", error);
    }
}

function actualizarResaltadoMusculos(regiones) {
    console.log("💪 Actualizando músculos:", regiones);
    
    // Limpiar todos los resaltados
    document.querySelectorAll('.body-diagram .region').forEach(el => {
        el.classList.remove('highlight');
    });

    if (!regiones || !regiones.length) {
        console.log("⚠️ No hay regiones para resaltar");
        return;
    }

    // Resaltar cada región
    regiones.forEach(region => {
        // Vista frontal
        const elFrente = document.getElementById(region);
        if (elFrente) {
            elFrente.classList.add('highlight');
        }
        
        // Vista trasera
        const elEspalda = document.getElementById(region + '-back');
        if (elEspalda) {
            elEspalda.classList.add('highlight');
        }

        // Ajustes para casos especiales
        if (region === 'shoulders') {
            const elShouldersEspalda = document.getElementById('shoulders-back');
            if (elShouldersEspalda) {
                elShouldersEspalda.classList.add('highlight');
            }
        }
        if (region === 'quads') {
            const elQuadsEspalda = document.getElementById('quads-back');
            if (elQuadsEspalda) {
                elQuadsEspalda.classList.add('highlight');
            }
        }
        if (region === 'calves') {
            const elCalvesEspalda = document.getElementById('calves-back');
            if (elCalvesEspalda) {
                elCalvesEspalda.classList.add('highlight');
            }
        }
    });
}

function configurarBotonesVistaCuerpo() {
    const botonesVista = document.querySelectorAll('.view-btn');
    
    botonesVista.forEach(boton => {
        boton.addEventListener('click', function() {
            // Desactivar todos los botones
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            // Activar el botón actual
            this.classList.add('active');

            const vista = this.dataset.view;
            
            // Ocultar todas las vistas
            document.querySelectorAll('.body-svg').forEach(svg => svg.classList.remove('active'));
            
            // Mostrar la vista correspondiente
            if (vista === 'front') {
                document.querySelector('.body-front').classList.add('active');
            } else if (vista === 'back') {
                document.querySelector('.body-back').classList.add('active');
            }
        });
    });
}
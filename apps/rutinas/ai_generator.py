# apps/rutinas/ai_generator.py
# ============================================================
#  BIO-FIT — Motor de Generación de Rutinas con IA (Groq)
#  CORRECCIÓN: RoutineGeneratorAI eliminada (código muerto/roto).
#  _build_user_prompt incorpora el inventario real del gimnasio.
# ============================================================

import json
import random
import random
from groq import Groq
from django.conf import settings

<<<<<<< Updated upstream
SYSTEM_PROMPT = """Eres un entrenador personal de élite, experto y certificado con más de 15 años de experiencia en diseño de programas biomecánicos para gimnasio y calistenia.

Tu única tarea es generar planes de entrenamiento SEMANALES completos, DETALLADOS y 100% PERSONALIZADOS en español.

═══════════════════════════════════════════════════════════
REGLAS DE FORMATO — NUNCA LAS VIOLES:
═══════════════════════════════════════════════════════════
- Está PROHIBIDO devolver siempre los mismos ejercicios.
- Debes alterar completamente la selección de ejercicios, el orden, los rangos de repeticiones, las series y los tiempos de descanso en función de los parámetros de nivel y objetivo que te provea el usuario.
- Analiza científicamente lo que implica cada objetivo para estructurar entrenamientos únicos y funcionales.

═══════════════════════════════════════════════════════════
REGLAS DE FORMATO — NUNCA LAS VIOLES:
═══════════════════════════════════════════════════════════
REGLA 1 — FORMATO DE RESPUESTA:
Responde ÚNICAMENTE con un objeto JSON válido. Sin texto antes ni después. Sin markdown. Solo JSON puro.

REGLA 2 — ESTRUCTURA OBLIGATORIA:
El JSON debe tener una clave "dias" que contiene una lista de objetos.
Cada objeto representa UN DÍA de entrenamiento con EXACTAMENTE estas claves:
  "dia"        → número del día como string: "Día 1", "Día 2", etc.
  "enfoque"    → grupo muscular o tipo de entrenamiento del día (ej: "Tren Superior", "Cardio y Core")
  "calentamiento"          → lista de ejercicios
  "entrenamiento_principal" → lista de ejercicios
  "estiramiento"            → lista de ejercicios

REGLA 3 — ESTRUCTURA DE CADA EJERCICIO:
Cada ejercicio tiene EXACTAMENTE estas 5 claves:
  "ejercicio"     → nombre real y específico (NUNCA genérico)
  "series"        → string (ej. "4")
  "repeticiones"  → string (ej. "12", "12-15", "30 seg")
  "descanso"      → string (ej. "60 seg", "90 seg")
  "nota"          → tip técnico breve en español

REGLA 4 — EQUIPAMIENTO:
SOLO usa ejercicios con el equipamiento listado. Sin excepciones.

REGLA 5 — DISTRIBUCIÓN MUSCULAR:
Distribuye los grupos musculares de forma inteligente para asegurar recuperación adecuada entre días.
Ejemplo para 3 días: Día1=Tren Superior Empuje | Día2=Tren Inferior | Día3=Tren Superior Jale+Core
Ejemplo para 4 días: Día1=Pecho+Tríceps | Día2=Espalda+Bíceps | Día3=Piernas | Día4=Hombros+Core
Ejemplo para 5 días: Día1=Pecho | Día2=Espalda | Día3=Piernas | Día4=Hombros | Día5=Brazos+Core

REGLA 6 — CANTIDAD POR DÍA:
  - calentamiento: 3 ejercicios
  - entrenamiento_principal: 5 a 7 ejercicios
  - estiramiento: 3 ejercicios
"""


def _build_user_prompt(user_data: dict) -> str:
    """Construye el mensaje del usuario con sus datos específicos."""
    nivel      = user_data.get("nivel", "intermedio")
    objetivo   = user_data.get("objetivo", "salud_general")
    dias       = user_data.get("dias", 3)
    lugar      = user_data.get("lugar", "gimnasio")
    lesiones   = user_data.get("lesiones", "ninguna")
    edad       = user_data.get("edad", "")
    peso       = user_data.get("peso", "")
    genero     = user_data.get("genero", "")

    # ── Equipamiento real del gimnasio ────────────────────────────────────────
    inventario = user_data.get("inventario_gimnasio", [])
    if inventario:
        nombres = [e.get("nombre", "").strip() for e in inventario if e.get("nombre")]
        equipo  = ", ".join(nombres) if nombres else "equipamiento completo de gimnasio"
        lugar   = "gimnasio"
        fuente_equipo = "equipos REALES registrados en el gimnasio del usuario"
    elif lugar == "casa":
        equipo = "peso corporal y colchoneta únicamente (SIN máquinas)"
        fuente_equipo = "entrenamiento en casa"
    else:
        equipo = "equipamiento completo de gimnasio"
        fuente_equipo = "gimnasio genérico"

    objetivos_map = {
        'perder_peso':   'Pérdida de grasa y definición muscular',
        'ganar_musculo': 'Hipertrofia y ganancia de masa muscular',
        'resistencia':   'Resistencia cardiovascular y capacidad aeróbica',
        'fuerza':        'Fuerza máxima y potencia',
        'tonificar':     'Tonificación y mejora estética',
        'salud_general': 'Salud general y bienestar',
        'mantenimiento': 'Mantenimiento del estado físico actual',
    }
    objetivo_desc = objetivos_map.get(objetivo, objetivo.replace('_', ' '))

    adaptacion_nivel = {
        'principiante': "Máquinas guiadas, poleas o peso corporal. Descansos amplios. Movimientos simples.",
        'intermedio':   "Pesos libres combinados con máquinas. Superseries simples. Compuestos moderados.",
        'avanzado':     "Pesos libres, superseries, poliarticulares complejos, sobrecarga progresiva.",
    }
    adaptacion = adaptacion_nivel.get(nivel, adaptacion_nivel['intermedio'])

    seed_id = random.randint(1000, 9999)

    perfil = f"Nivel: {nivel} | Objetivo: {objetivo_desc} | Días/semana: {dias} | Lugar: {lugar}"
    if edad:   perfil += f" | Edad: {edad} años"
    if peso:   perfil += f" | Peso: {peso} kg"
    if genero: perfil += f" | Género: {genero}"

    # Construir ejemplo de estructura JSON con N días
    dias_ejemplo = "\n    ".join([
        f'{{"dia": "Día {i+1}", "enfoque": "...", "calentamiento": [...], "entrenamiento_principal": [...], "estiramiento": [...]}}'
        for i in range(dias)
    ])

    return f"""Genera un plan de entrenamiento semanal de EXACTAMENTE {dias} DÍAS (Request ID: {seed_id}).

PERFIL DEL USUARIO:
{perfil}
Lesiones o limitaciones: {lesiones}

ORIENTACIÓN DE EJERCICIOS PARA ESTE OBJETIVO:
{ejercicios_sugeridos}

INSTRUCCIONES CRÍTICAS:
1. USA nombres de ejercicios REALES Y ESPECÍFICOS (ver ejemplos en tus instrucciones de sistema).
2. El entrenamiento principal debe incluir una mezcla de ejercicios COMPUESTOS e AISLAMIENTO.
3. Adapta las series/repeticiones al nivel "{nivel}" y objetivo "{objetivo_desc}".
4. Responde SOLO con el JSON, sin texto adicional.
5. EQUIPAMIENTO OBLIGATORIO: SOLO puedes usar ejercicios que se realicen con el equipamiento listado arriba. NO inventes ni uses máquinas o implementos que no estén en la lista. Si el usuario entrena en casa, usa únicamente ejercicios con peso corporal.

FORMATO JSON REQUERIDO (ejemplo de estructura — usa ejercicios reales, no estos):
{{
  "calentamiento": [
    {{"ejercicio": "Trote suave en cinta", "series": "1", "repeticiones": "5 min", "descanso": "0 seg", "nota": "Ritmo ligero para elevar temperatura corporal"}},
    {{"ejercicio": "Rotaciones de hombros con banda", "series": "2", "repeticiones": "15", "descanso": "20 seg", "nota": "Movimiento circular completo, adelante y atrás"}},
    {{"ejercicio": "Sentadillas sin peso", "series": "2", "repeticiones": "12", "descanso": "20 seg", "nota": "Profundidad completa, rodillas alineadas con pies"}}
  ],
  "entrenamiento_principal": [
    {{"ejercicio": "Press de banca con barra plana", "series": "4", "repeticiones": "10", "descanso": "90 seg", "nota": "Baja la barra hasta el pecho de forma controlada en 3 segundos"}},
    {{"ejercicio": "Remo con barra pronado", "series": "4", "repeticiones": "10", "descanso": "90 seg", "nota": "Codo al cuerpo, aprieta la espalda en el punto de contracción"}},
    {{"ejercicio": "Sentadilla trasera con barra", "series": "4", "repeticiones": "8", "descanso": "120 seg", "nota": "Cadera por debajo de rodillas, core activado todo el recorrido"}},
    {{"ejercicio": "Prensa de pierna 45 grados", "series": "3", "repeticiones": "12", "descanso": "75 seg", "nota": "No bloquees las rodillas al extender, pies al ancho de hombros"}},
    {{"ejercicio": "Curl de bíceps con mancuerna alternado", "series": "3", "repeticiones": "12", "descanso": "60 seg", "nota": "Supina la muñeca en el punto de máxima contracción"}},
    {{"ejercicio": "Extensión de tríceps en polea alta con cuerda", "series": "3", "repeticiones": "14", "descanso": "60 seg", "nota": "Codos fijos al costado, extiende completamente al fondo"}},
    {{"ejercicio": "Elevaciones laterales con mancuernas", "series": "3", "repeticiones": "15", "descanso": "45 seg", "nota": "Codos ligeramente flexionados, sube hasta paralelo al suelo"}}
  ],
  "estiramiento": [
    {{"ejercicio": "Estiramiento de cuádriceps de pie", "series": "1", "repeticiones": "30 seg por pierna", "descanso": "10 seg", "nota": "Apoya una mano en la pared para equilibrio"}},
    {{"ejercicio": "Estiramiento de pectoral en marco de puerta", "series": "1", "repeticiones": "30 seg", "descanso": "10 seg", "nota": "Antebrazo apoyado en el marco, rota el tronco suavemente"}},
    {{"ejercicio": "Estiramiento de isquiotibiales sentado", "series": "1", "repeticiones": "30 seg por pierna", "descanso": "10 seg", "nota": "Columna recta, inclina el tronco desde la cadera"}}
  ]
}}

Ahora genera la rutina REAL para el usuario. Usa ejercicios específicos y variados."""


class RoutineGeneratorAI:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        # llama-3.3-70b-versatile sigue instrucciones JSON mucho mejor que 8b
        self.model_name = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
        """
        Extrae de forma dinámica y rigurosa los datos del formulario de BIO-FIT.
        Introduce un token de entropía aleatoria para romper el caché estático del modelo de Groq.
        """
        nivel = str(user_data.get('nivel', 'principiante')).strip().lower()
        objetivo = str(user_data.get('objetivo', 'salud_general')).strip().lower()
        dias = str(user_data.get('dias', '3')).strip()


        # Reemplazar guiones bajos por espacios legibles para mejor contexto semántico de la IA
        objetivo_limpio = objetivo.replace('_', ' ')
        
        # Generador de entropía interna para obligar al modelo a recalcular la respuesta desde cero
        seed_id = random.randint(1000, 9999)

        return f"""Genera un plan de entrenamiento totalmente inédito y específico en formato JSON (Request ID: {seed_id}).
=======

# ── Prompt del sistema ────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un entrenador personal certificado NSCA-CSCS con experiencia en periodización del entrenamiento para atletas recreacionales y de alto rendimiento.

Tu única función es generar rutinas de ejercicio en formato JSON, siguiendo las instrucciones del usuario con precisión científica.

═══════════════════════════════════════════════════════════════════
PRINCIPIOS OBLIGATORIOS DE DISEÑO:
═══════════════════════════════════════════════════════════════════

PRINCIPIO 1 — RESTRICCIÓN DE EQUIPAMIENTO (REGLA MÁS IMPORTANTE):
Si el usuario tiene una lista de equipamiento disponible, SOLO puedes usar ejercicios
que se ejecuten con ese equipamiento exacto. NUNCA inventes máquinas que no estén en la lista.
Si el usuario entrena en casa (sin equipamiento), usa ÚNICAMENTE ejercicios con peso corporal.

PRINCIPIO 2 — ESPECIFICIDAD FISIOLÓGICA POR OBJETIVO:
  • Hipertrofia/ganar músculo : 4-5 series × 8-12 reps | descanso 75-120 seg
  • Fuerza máxima             : 5-6 series × 1-5 reps  | descanso 3-5 min
  • Pérdida de grasa          : 3-4 series × 12-20 reps | descanso 30-60 seg
  • Resistencia               : 2-4 series × 15-25 reps | descanso 20-45 seg
  • Tonificación/salud general: 3 series × 10-15 reps   | descanso 60-90 seg

PRINCIPIO 3 — DIFERENCIACIÓN POR NIVEL:
  • Principiante : SOLO máquinas guiadas, cables con guía o peso corporal. NUNCA barra libre.
  • Intermedio   : Mancuernas, cables libres, máquinas. Puede incluir superseries.
  • Avanzado     : Barra olímpica, movimientos complejos, técnicas de intensidad (drop sets, rest-pause).

PRINCIPIO 4 — VARIABILIDAD:
Genera una rutina diferente en cada solicitud. Rota patrones de movimiento,
orden de grupos musculares y métodos de entrenamiento.

═══════════════════════════════════════════════════════════════════
FORMATO DE RESPUESTA — REGLAS ABSOLUTAS:
═══════════════════════════════════════════════════════════════════

REGLA 1: Responde ÚNICAMENTE con JSON válido. Sin texto antes ni después. Sin bloques markdown.

REGLA 2: El JSON debe tener EXACTAMENTE estas 3 claves en minúsculas:
  "calentamiento"
  "entrenamiento_principal"
  "estiramiento"

REGLA 3: Cada ejercicio es un objeto con EXACTAMENTE estas 5 claves:
  "ejercicio"     → Nombre técnico completo. NUNCA genérico. Ej: "Press inclinado con mancuernas agarre neutro"
  "series"        → String numérico. Ej: "4"
  "repeticiones"  → Rango o número. Ej: "8-10", "12", "30 seg"
  "descanso"      → Tiempo preciso. Ej: "90 seg", "2 min"
  "nota"          → Instrucción técnica concreta en formato "[PUNTO CLAVE]: [acción]"
                    Ej: "ACTIVACIÓN: Contrae el glúteo en la posición superior antes de bajar"
                    NUNCA escribas notas genéricas como "Mantén buena postura".
"""


# ── Mapas de contexto científico por objetivo ─────────────────────────────────
_OBJETIVO_CONTEXTO = {
    'ganar_musculo': {
        'metodo':   'hipertrofia sarcomérica y sarcoplásmica',
        'series':   '4-5', 'reps': '6-12', 'descanso': '75-120 seg',
        'enfoque':  'tensión mecánica máxima, rango completo de movimiento, conexión mente-músculo',
        'tecnica':  'tempo controlado 3-1-1 (excéntrico-pausa-concéntrico)',
    },
    'perder_peso': {
        'metodo':   'déficit calórico por alta densidad metabólica',
        'series':   '3-4', 'reps': '12-20', 'descanso': '30-60 seg',
        'enfoque':  'circuitos metabólicos, ejercicios multiarticulares, mínimo descanso',
        'tecnica':  'movimientos explosivos controlados, transiciones rápidas',
    },
    'fuerza': {
        'metodo':   'adaptación neuromuscular y reclutamiento de unidades motoras',
        'series':   '5-6', 'reps': '1-5', 'descanso': '3-5 min',
        'enfoque':  'movimientos compuestos pesados, técnica impecable bajo carga máxima',
        'tecnica':  'bracing abdominal total, path de barra consistente',
    },
    'resistencia': {
        'metodo':   'adaptaciones cardiovasculares y musculares de resistencia',
        'series':   '2-4', 'reps': '15-25 o 30-60 seg', 'descanso': '20-45 seg',
        'enfoque':  'trabajo aeróbico-anaeróbico mixto, resistencia muscular local',
        'tecnica':  'respiración rítmica, cadencia constante, postura dinámica eficiente',
    },
    'tonificar': {
        'metodo':   'recomposición corporal moderada',
        'series':   '3-4', 'reps': '12-15', 'descanso': '45-75 seg',
        'enfoque':  'definición muscular con preservación de masa, trabajo cardiovascular integrado',
        'tecnica':  'contracción isométrica en el punto de máxima tensión, fase excéntrica lenta',
    },
    'salud_general': {
        'metodo':   'acondicionamiento físico integral y funcional',
        'series':   '3', 'reps': '10-15', 'descanso': '60-90 seg',
        'enfoque':  'patrones de movimiento funcionales (empuje, jalón, bisagra, sentadilla, rotación)',
        'tecnica':  'calidad de movimiento sobre cantidad, progresión gradual',
    },
    'flexibilidad': {
        'metodo':   'movilidad articular y elongación muscular progresiva',
        'series':   '2-3', 'reps': '30-60 seg por lado', 'descanso': '20-30 seg',
        'enfoque':  'rango de movimiento activo, movilidad articular, liberación miofascial',
        'tecnica':  'respiración diafragmática profunda, relajación progresiva',
    },
}

_NIVEL_CONTEXTO = {
    'principiante': {
        'equipo':      'SOLO máquinas guiadas, poleas con guía o peso corporal. PROHIBIDO barra libre.',
        'volumen':     'no más de 10-12 ejercicios en total',
        'extra':       'Nota de seguridad obligatoria en TODOS los ejercicios. Priorizar aprendizaje motor.',
    },
    'intermedio': {
        'equipo':      'mancuernas, cables libres, barra con técnica establecida, máquinas',
        'volumen':     '12-16 ejercicios en total',
        'extra':       'Puede incluir superseries y técnicas básicas de intensidad.',
    },
    'avanzado': {
        'equipo':      'barra olímpica, movimientos olímpicos, kettlebells, todos los equipos',
        'volumen':     '14-20 ejercicios en total',
        'extra':       'OBLIGATORIO incluir al menos una técnica de intensidad: drop set, rest-pause o cluster set.',
    },
}

# Patrones de movimiento rotatorios para garantizar variedad estructural
_PATRONES = [
    "empuje horizontal → jalón vertical → bisagra de cadera → sentadilla",
    "empuje vertical → jalón horizontal → sentadilla unilateral → empuje accesorio",
    "jalón vertical neutro → empuje inclinado → bisagra unilateral → circuito metabólico",
    "empuje en cable → remo horizontal → sentadilla frontal → hip thrust",
    "press unilateral → jalón en polea baja → peso muerto → step-up compuesto",
]


def _formatear_inventario(inventario: list) -> str:
    """
    Convierte la lista de documentos de Firestore en un texto legible
    para el prompt de la IA, agrupando por nombre y tipo.
    """
    if not inventario:
        return "Sin equipamiento de gimnasio (usar solo peso corporal)"

    lineas = []
    for equipo in inventario:
        nombre = equipo.get('nombre', '').strip()
        tipo   = equipo.get('tipo',   '').strip()
        estado = equipo.get('estado', 'disponible').strip()
        cant   = equipo.get('cantidad', 1)

        # Solo incluir equipos disponibles en buen estado
        if estado in ('fuera_de_servicio',):
            continue

        linea = f"  • {nombre}"
        if tipo:
            linea += f" ({tipo})"
        if cant and int(cant) > 1:
            linea += f" × {cant} unidades"
        if estado == 'mantenimiento':
            linea += " [en mantenimiento — usa con precaución]"
        lineas.append(linea)

    return "\n".join(lineas) if lineas else "Sin equipamiento operativo disponible"


def _build_user_prompt(user_data: dict) -> str:
    """
    Construye el prompt de usuario con todos los parámetros del perfil
    e inyecta el inventario real del gimnasio para que la IA solo
    prescriba ejercicios con equipos que realmente existen.
    """
    nivel    = str(user_data.get('nivel',    'principiante')).strip().lower()
    objetivo = str(user_data.get('objetivo', 'salud_general')).strip().lower()
    dias     = str(user_data.get('dias',     '3')).strip()
    lugar    = str(user_data.get('lugar',    'gimnasio')).strip().lower()
    lesiones = str(user_data.get('lesiones', 'ninguna')).strip()
    edad     = str(user_data.get('edad',     '')).strip()
    peso     = str(user_data.get('peso',     '')).strip()
    genero   = str(user_data.get('genero',   '')).strip()

    objetivo_limpio = objetivo.replace('_', ' ')

    # Contexto científico del objetivo y nivel
    ctx_obj = _OBJETIVO_CONTEXTO.get(objetivo, _OBJETIVO_CONTEXTO['salud_general'])
    ctx_niv = _NIVEL_CONTEXTO.get(nivel,       _NIVEL_CONTEXTO['principiante'])
>>>>>>> Stashed changes

    # Inventario real del gimnasio (o texto de fallback para casa)
    inventario_raw  = user_data.get('inventario_gimnasio', [])
    inventario_texto = _formatear_inventario(inventario_raw)

    # Variedad estructural
    patron_sesion = random.choice(_PATRONES)
    seed_id       = random.randint(10000, 99999)

    # Construir líneas de perfil opcionales
    perfil_extra = []
    if edad:    perfil_extra.append(f"Edad: {edad} años")
    if peso:    perfil_extra.append(f"Peso: {peso} kg")
    if genero:  perfil_extra.append(f"Género: {genero}")
    perfil_extra_txt = " | ".join(perfil_extra) if perfil_extra else "No especificado"

    return f"""SOLICITUD BIO-FIT · ID:{seed_id}

════════════════════════════════════════
PERFIL DEL ATLETA
════════════════════════════════════════
Nivel de experiencia : {nivel}
Objetivo principal   : {objetivo_limpio}
Días disponibles     : {dias} días/semana
Lugar de entrenamiento: {lugar}
Lesiones/Limitaciones: {lesiones}
Datos adicionales    : {perfil_extra_txt}

════════════════════════════════════════
EQUIPAMIENTO DISPONIBLE EN EL GIMNASIO
════════════════════════════════════════
{inventario_texto}

⚠️  RESTRICCIÓN CRÍTICA: Solo puedes prescribir ejercicios que se realicen
    con el equipamiento listado arriba. Si el campo dice "peso corporal",
    usa ÚNICAMENTE ejercicios sin ningún equipo adicional.

════════════════════════════════════════
PARÁMETROS CIENTÍFICOS PARA ESTE OBJETIVO
════════════════════════════════════════
Método de entrenamiento : {ctx_obj['metodo']}
Series prescritas       : {ctx_obj['series']} por ejercicio
Rango de repeticiones   : {ctx_obj['reps']}
Descanso entre series   : {ctx_obj['descanso']}
Enfoque principal       : {ctx_obj['enfoque']}
Técnica específica      : {ctx_obj['tecnica']}

════════════════════════════════════════
RESTRICCIONES POR NIVEL: {nivel.upper()}
════════════════════════════════════════
Equipamiento autorizado : {ctx_niv['equipo']}
Volumen total sesión    : {ctx_niv['volumen']}
Consideración especial  : {ctx_niv['extra']}

════════════════════════════════════════
ESTRUCTURA DE MOVIMIENTO PARA ESTA SESIÓN
════════════════════════════════════════
Patrón asignado: {patron_sesion}

════════════════════════════════════════
INSTRUCCIÓN FINAL
════════════════════════════════════════
Genera UNA rutina completa para UN solo día de entrenamiento.
— Respeta todos los parámetros científicos y el equipamiento disponible.
— Cada "nota" debe seguir el formato: "[PUNTO CLAVE]: [instrucción concreta]".
— NUNCA uses nombres de ejercicio genéricos.
— Genera una rutina diferente a cualquier respuesta anterior.
"""


# ── Claves de validación estructural ─────────────────────────────────────────
_REQUIRED_ROOT_KEYS = {'calentamiento', 'entrenamiento_principal', 'estiramiento'}
_REQUIRED_EXER_KEYS = {'ejercicio', 'series', 'repeticiones', 'descanso', 'nota'}


class RoutineGenerator:
    """
    Clase principal del motor de IA de BIO-FIT.
    Genera rutinas de entrenamiento personalizadas usando Groq (LLaMA 3.3 70B).
    """

    def __init__(self):
        api_key = getattr(settings, "GROQ_API_KEY", None)
<<<<<<< Updated upstream
        self.client = Groq(api_key=api_key) if api_key else None
        self.model_name = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
        print(f"[BIO-FIT] Motor de IA cargado: {self.model_name}")

    def generate_routine(self, user_data: dict) -> dict:
        if not self.client:
            return {'success': False, 'error': 'La API Key de Groq no está configurada.'}
=======
        self.client     = Groq(api_key=api_key) if api_key else None
        self.model_name = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
        print(f"[BIO-FIT] Motor IA inicializado — modelo: {self.model_name}")

    def generate_routine(self, user_data: dict) -> dict:
        """
        Genera una rutina completa de entrenamiento.

        Args:
            user_data: dict con nivel, objetivo, dias, lugar, lesiones,
                       inventario_gimnasio (lista de Firestore), y datos opcionales.

        Returns:
            {'success': True, 'routine': {...}}  si todo va bien.
            {'success': False, 'error': '...'}  si hay algún problema.
        """
        if not self.client:
            print("[BIO-FIT] ERROR: GROQ_API_KEY no configurada.")
            return {'success': False, 'error': 'La API Key de Groq no está configurada.'}

        content = None
>>>>>>> Stashed changes
        try:
            user_msg = _build_user_prompt(user_data)

            inventario = user_data.get("inventario_gimnasio", [])
            if inventario:
                nombres = [e.get("nombre", "") for e in inventario if e.get("nombre")]
                print(f"[BIO-FIT] Equipos enviados a la IA: {', '.join(nombres)}")
            else:
                print(f"[BIO-FIT] Sin inventario — modo: {user_data.get('lugar', 'desconocido')}")

            response = self.client.chat.completions.create(
                model    = self.model_name,
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
<<<<<<< Updated upstream
                temperature=0.75,
                max_tokens=6000,  # Aumentado para soportar múltiples días
                response_format={"type": "json_object"},
=======
                # 0.85: máxima variedad en selección de ejercicios
                # manteniendo coherencia en el formato JSON.
                temperature     = 0.85,
                max_tokens      = 3500,
                response_format = {"type": "json_object"},
>>>>>>> Stashed changes
            )

            content       = response.choices[0].message.content
            if not content:
                return {'success': False, 'error': 'La IA no devolvió contenido.'}

            content_limpio = self._limpiar_json(content)
            routine_json   = json.loads(content_limpio)

            # Validar estructura antes de devolver
            error_estructura = self._validar_estructura(routine_json)
            if error_estructura:
                print(f"[BIO-FIT] Estructura inválida: {error_estructura}")
                return {'success': False, 'error': f'Estructura de rutina inválida: {error_estructura}'}

            return {'success': True, 'routine': routine_json}

        except json.JSONDecodeError as e:
<<<<<<< Updated upstream
            print(f"[BIO-FIT] JSON inválido de Groq: {e}")
=======
            snippet = content[:500] if content else "vacío"
            print(f"[BIO-FIT] JSON inválido de Groq: {e} | Contenido: {snippet}")
>>>>>>> Stashed changes
            return {'success': False, 'error': 'La IA devolvió un formato inesperado. Inténtalo de nuevo.'}
        except Exception as e:
            print(f"[BIO-FIT] Error crítico en Groq: {e}")
            return {'success': False, 'error': f'Error de conexión con el motor de IA: {str(e)}'}

    def _limpiar_json(self, texto: str) -> str:
<<<<<<< Updated upstream
        texto = texto.strip()
        texto = re.sub(r'^```(?:json)?\s*', '', texto, flags=re.MULTILINE)
        texto = re.sub(r'\s*```$', '', texto, flags=re.MULTILINE)
        inicio = texto.find('{')
        fin    = texto.rfind('}')
        if inicio != -1 and fin != -1:
            return texto[inicio:fin+1]
        return texto


=======
        """Elimina residuos de markdown que puedan romper el parseo."""
        t = texto.strip()
        if t.startswith("```json"):
            t = t[7:]
        elif t.startswith("```"):
            t = t[3:]
        if t.endswith("```"):
            t = t[:-3]
        return t.strip()

    def _validar_estructura(self, data: dict) -> str | None:
        """
        Valida que el JSON tenga las claves raíz correctas y que cada
        ejercicio contenga los 5 campos requeridos.

        Returns:
            None si la estructura es válida.
            Mensaje de error descriptivo si algo falla.
        """
        # Verificar claves raíz
        faltantes_raiz = _REQUIRED_ROOT_KEYS - set(data.keys())
        if faltantes_raiz:
            return f"Faltan claves raíz: {faltantes_raiz}"

        # Verificar estructura interna de cada bloque
        for bloque in _REQUIRED_ROOT_KEYS:
            ejercicios = data.get(bloque, [])
            if not isinstance(ejercicios, list):
                return f"'{bloque}' debe ser una lista, recibido: {type(ejercicios).__name__}"
            for i, ej in enumerate(ejercicios):
                if not isinstance(ej, dict):
                    return f"Ejercicio #{i} en '{bloque}' no es un objeto dict"
                campos_faltantes = _REQUIRED_EXER_KEYS - set(ej.keys())
                if campos_faltantes:
                    return f"Ejercicio #{i} en '{bloque}' le faltan: {campos_faltantes}"

        return None  # Estructura válida ✅


# Instancia única reutilizable para toda la aplicación (patrón Singleton)
>>>>>>> Stashed changes
routine_generator = RoutineGenerator()
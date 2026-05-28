import json
import re
import random
import random
from groq import Groq
from django.conf import settings

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

PARÁMETROS DEL CLIENTE BIO-FIT:
- Nivel de experiencia real: {nivel}
- Objetivo principal: {objetivo_limpio}
- Días disponibles a la semana: {dias} días

REQUERIMIENTOS EXCLUSIVOS DE ADAPTACIÓN BIOMECÁNICA:
1. Si el nivel es 'principiante', prescribe ejercicios en máquinas guiadas, poleas fijas o peso corporal controlado para mitigar riesgos de lesión, con descansos amplios.
2. Si el nivel es 'intermedio' o 'avanzado', prescribe variantes avanzadas utilizando pesos libres (barras, mancuernas), superseries, movimientos compuestos poliarticulares complejos y técnicas de sobrecarga progresiva.
3. Si el objetivo es 'perder peso' o 'resistencia', el entrenamiento principal debe enfocarse en alta densidad metabólica (ejercicios multiarticulares combinados, repeticiones altas entre 12 y 15, y descansos cortos de 45-60 seg).
4. Si el objetivo es 'ganar musculo' (hipertrofia) o 'fuerza', enfócate en rangos pesados o moderados (6-10 repeticiones), con mayor volumen de series y descansos de 90 seg a 3 min.

Adapta el plan de forma estricta a un usuario {nivel} que busca {objetivo_limpio}. No copies respuestas anteriores."""


class RoutineGenerator:
    def __init__(self):
        api_key = getattr(settings, "GROQ_API_KEY", None)
        self.client = Groq(api_key=api_key) if api_key else None
        self.model_name = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
        print(f"[BIO-FIT] Motor de IA cargado: {self.model_name}")

    def generate_routine(self, user_data: dict) -> dict:
        if not self.client:
            return {'success': False, 'error': 'La API Key de Groq no está configurada.'}
        try:
            user_msg = _build_user_prompt(user_data)

            inventario = user_data.get("inventario_gimnasio", [])
            if inventario:
                nombres = [e.get("nombre", "") for e in inventario if e.get("nombre")]
                print(f"[BIO-FIT] Equipos enviados a la IA: {', '.join(nombres)}")
            else:
                print(f"[BIO-FIT] Sin inventario — modo: {user_data.get('lugar', 'desconocido')}")

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.75,
                max_tokens=6000,  # Aumentado para soportar múltiples días
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                return {'success': False, 'error': 'La IA no devolvió contenido.'}

            content_limpio = self._limpiar_json(content)
            routine_json   = json.loads(content_limpio)

            return {'success': True, 'routine': routine_json}

        except json.JSONDecodeError as e:
            print(f"[BIO-FIT] JSON inválido de Groq: {e}")
            return {'success': False, 'error': 'La IA devolvió un formato inesperado. Inténtalo de nuevo.'}
        except Exception as e:
            print(f"[BIO-FIT] Error crítico en Groq: {e}")
            return {'success': False, 'error': f'Error de conexión con el motor de IA: {str(e)}'}

    def _limpiar_json(self, texto: str) -> str:
        texto = texto.strip()
        texto = re.sub(r'^```(?:json)?\s*', '', texto, flags=re.MULTILINE)
        texto = re.sub(r'\s*```$', '', texto, flags=re.MULTILINE)
        inicio = texto.find('{')
        fin    = texto.rfind('}')
        if inicio != -1 and fin != -1:
            return texto[inicio:fin+1]
        return texto


routine_generator = RoutineGenerator()
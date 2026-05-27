import json
import re
from groq import Groq
from django.conf import settings

# ── Prompt del sistema ─────────────────────────────────────────────────────────
# Embebido directamente aquí para tener control total sobre lo que recibe la IA.
SYSTEM_PROMPT = """Eres un entrenador personal experto y certificado con más de 15 años de experiencia
en diseño de programas de entrenamiento para gimnasio y calistenia.

Tu única tarea es generar rutinas de ejercicio DETALLADAS y PROFESIONALES en español.

═══════════════════════════════════════════════════════════
REGLAS ABSOLUTAS — NUNCA LAS VIOLES:
═══════════════════════════════════════════════════════════

REGLA 1 — FORMATO DE RESPUESTA:
Responde ÚNICAMENTE con un objeto JSON válido. Sin texto antes ni después.
Sin explicaciones, sin markdown, sin bloques ```json```. Solo el JSON puro.

REGLA 2 — ESTRUCTURA OBLIGATORIA DEL JSON:
El JSON debe tener EXACTAMENTE estas 3 claves principales, sin más, sin menos:
  "calentamiento"
  "entrenamiento_principal"
  "estiramiento"

REGLA 3 — ESTRUCTURA DE CADA EJERCICIO:
Cada ejercicio es un objeto con EXACTAMENTE estas 5 claves en minúsculas:
  "ejercicio"     → nombre real y específico del ejercicio (NUNCA genérico)
  "series"        → número de series como string (ej. "4")
  "repeticiones"  → reps o tiempo como string (ej. "12" o "30 seg")
  "descanso"      → tiempo de descanso (ej. "60 seg" o "90 seg")
  "nota"          → instrucción técnica breve en español

REGLA 4 — NOMBRES DE EJERCICIOS (LA MÁS IMPORTANTE):
NUNCA uses nombres genéricos como "Ejercicio", "Ejercicio Personalizado", "Exercise".
SIEMPRE usa nombres reales y específicos. Ejemplos obligatorios:
  ✅ "Curl de bíceps con mancuerna alternado"
  ✅ "Press de banca con barra plana"
  ✅ "Sentadilla búlgara con mancuernas"
  ✅ "Remo con mancuerna a una mano"
  ✅ "Extensión de tríceps en polea alta"
  ✅ "Peso muerto convencional con barra"
  ✅ "Prensa de pierna 45 grados"
  ✅ "Elevaciones laterales con mancuernas"
  ✅ "Jalón al pecho en polea"
  ✅ "Hip thrust con barra"
  ✅ "Face pull en polea"
  ✅ "Lunges caminando con mancuernas"
  ✅ "Plancha abdominal isométrica"
  ✅ "Fondos en paralelas"
  ✅ "Dominadas con agarre supino"
  ✅ "Romanian deadlift con barra"
  ✅ "Leg curl en máquina acostado"
  ✅ "Extensión de cuádriceps en máquina"
  ✅ "Press militar con barra de pie"
  ✅ "Aperturas con mancuernas en banco inclinado"

REGLA 5 — CANTIDAD DE EJERCICIOS:
  - calentamiento: 3 a 4 ejercicios
  - entrenamiento_principal: 6 a 8 ejercicios (variados, sin repetir grupos musculares seguidos)
  - estiramiento: 3 a 4 ejercicios

REGLA 6 — IDIOMA:
Todo el contenido (ejercicios, notas, descripciones) en ESPAÑOL.
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

    # ── Inventario real del gimnasio ──────────────────────────────────────
    # Si viene la lista de equipos desde Firebase la usamos directamente.
    # Si el usuario entrena en casa o no hay inventario, usamos peso corporal.
    inventario = user_data.get("inventario_gimnasio", [])
    if inventario:
        nombres = [e.get("nombre", "") for e in inventario if e.get("nombre")]
        equipo  = ", ".join(nombres) if nombres else "equipamiento completo de gimnasio"
        lugar   = "gimnasio"
    elif lugar == "casa":
        equipo = "peso corporal, colchoneta (sin maquinas de gimnasio)"
    else:
        equipo = user_data.get("equipo", "equipamiento completo de gimnasio")

    # Mapear objetivo a descripción
    objetivos_map = {
        'perder_peso':         'Pérdida de grasa y definición muscular',
        'ganar_musculo':       'Hipertrofia y ganancia de masa muscular',
        'resistencia':         'Resistencia cardiovascular y capacidad aeróbica',
        'fuerza':              'Fuerza máxima y potencia',
        'tonificar':           'Tonificación y mejora de la condición física general',
        'salud_general':       'Salud general y bienestar',
        'mantenimiento':       'Mantenimiento del estado físico actual',
    }
    objetivo_desc = objetivos_map.get(objetivo, objetivo)

    # Ejercicios recomendados según objetivo
    ejercicios_objetivo = {
        'perder_peso': (
            "Prioriza circuitos metabólicos: sentadillas, lunges, peso muerto, "
            "press de banca, remo, burpees modificados, mountain climbers, "
            "kettlebell swings. Descansos cortos (30-45 seg)."
        ),
        'ganar_musculo': (
            "Prioriza ejercicios compuestos pesados: press de banca con barra, "
            "sentadilla con barra, peso muerto, press militar, dominadas, remo con barra, "
            "hip thrust, prensa de pierna. Complementa con aislamiento: curl de bíceps, "
            "extensión de tríceps en polea, elevaciones laterales, leg curl, leg extension. "
            "Descansos de 60-90 seg."
        ),
        'resistencia': (
            "Prioriza ejercicios de alta repetición y cardio funcional: sentadillas, "
            "lunges, step-ups, burpees, saltos, mountain climbers, remo en máquina, "
            "bicicleta estática, elíptica. Descansos cortos (20-30 seg)."
        ),
        'fuerza': (
            "Prioriza los grandes levantamientos: peso muerto con barra, sentadilla trasera, "
            "press de banca con barra, press militar con barra, remo con barra. "
            "Series de 3-5 reps con peso máximo. Descansos largos (2-3 min)."
        ),
    }
    ejercicios_sugeridos = ejercicios_objetivo.get(objetivo, ejercicios_objetivo['ganar_musculo'])

    perfil = f"Nivel: {nivel} | Objetivo: {objetivo_desc} | Días/semana: {dias} | Lugar: {lugar}"
    if edad:   perfil += f" | Edad: {edad} años"
    if peso:   perfil += f" | Peso: {peso} kg"
    if genero: perfil += f" | Género: {genero}"

    return f"""Genera una rutina de entrenamiento para UN SOLO DÍA con el siguiente perfil:

PERFIL DEL USUARIO:
{perfil}
Equipamiento disponible: {equipo}
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

    def _limpiar_json(self, texto: str) -> str:
        """Extrae el JSON aunque la IA lo envuelva en markdown u otro texto."""
        texto = texto.strip()
        # Quitar bloques ```json ... ```
        texto = re.sub(r'^```(?:json)?\s*', '', texto, flags=re.MULTILINE)
        texto = re.sub(r'\s*```$', '', texto, flags=re.MULTILINE)
        # Encontrar el primer { y último }
        inicio = texto.find('{')
        fin    = texto.rfind('}')
        if inicio != -1 and fin != -1:
            return texto[inicio:fin+1]
        return texto

    def generate_routine(self, user_data: dict) -> dict:
        """Genera una rutina de ejercicios con ejercicios reales y específicos."""
        try:
            user_msg = _build_user_prompt(user_data)

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.5,       # Menos temperatura = más preciso en el formato
                max_tokens=3000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                return {'success': False, 'error': 'La IA no devolvió contenido.'}

            content_limpio = self._limpiar_json(content)
            routine_json   = json.loads(content_limpio)

            return {'success': True, 'routine': routine_json}

        except json.JSONDecodeError as e:
            print(f"[BIO-FIT] JSON inválido de Groq: {e}\nContenido: {content[:500]}")
            return {'success': False, 'error': 'La IA devolvió un formato inesperado. Intenta de nuevo.'}
        except Exception as e:
            print(f"[BIO-FIT] Error en Groq: {e}")
            return {'success': False, 'error': f'Error al generar la rutina: {str(e)}'}


# Instancia única para importar en las vistas
routine_generator = RoutineGeneratorAI()
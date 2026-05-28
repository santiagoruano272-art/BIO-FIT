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
    nivel    = str(user_data.get("nivel", "intermedio")).strip().lower()
    objetivo = str(user_data.get("objetivo", "salud_general")).strip().lower()
    dias     = int(user_data.get("dias", 3))
    lugar    = user_data.get("lugar", "gimnasio")
    lesiones = user_data.get("lesiones", "ninguna")
    edad     = user_data.get("edad", "")
    peso     = user_data.get("peso", "")
    genero   = user_data.get("genero", "")

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

EQUIPAMIENTO DISPONIBLE ({fuente_equipo}):
{equipo}

⚠️ RESTRICCIÓN CRÍTICA: Usa EXCLUSIVAMENTE ejercicios realizables con el equipamiento listado arriba.

ADAPTACIÓN POR NIVEL ({nivel}):
{adaptacion}

OBJETIVO ({objetivo_desc}):
Adapta la intensidad, series, repeticiones y descansos al objetivo indicado.

INSTRUCCIONES:
1. Genera EXACTAMENTE {dias} días de entrenamiento — ni más, ni menos.
2. Cada día debe tener un enfoque muscular distinto para permitir recuperación adecuada.
3. Usa nombres de ejercicios REALES, ESPECÍFICOS y VARIADOS entre días.
4. Responde SOLO con el JSON puro.

ESTRUCTURA JSON REQUERIDA:
{{
  "dias": [
    {dias_ejemplo}
  ]
}}"""


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
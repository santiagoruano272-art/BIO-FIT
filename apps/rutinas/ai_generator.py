import json
import re
import random
from groq import Groq
from django.conf import settings

# ── Prompt del sistema — Optimizado para evitar repeticiones en modo JSON ─────
SYSTEM_PROMPT = """Eres un entrenador personal de élite, experto y certificado con más de 15 años de experiencia en diseño de programas biomecánicos para gimnasio y calistenia.

Tu única tarea es generar rutinas de ejercicio ALTAMENTE DETALLADAS, PROFESIONALES y 100% PERSONALIZADAS en español.

═══════════════════════════════════════════════════════════
REGLAS DE DINAMISMO Y VARIABILIDAD ABSOLUTA:
═══════════════════════════════════════════════════════════
- Está PROHIBIDO devolver siempre los mismos ejercicios.
- Debes alterar completamente la selección de ejercicios, el orden, los rangos de repeticiones, las series y los tiempos de descanso en función de los parámetros de nivel y objetivo que te provea el usuario.
- Analiza científicamente lo que implica cada objetivo para estructurar entrenamientos únicos y funcionales.

═══════════════════════════════════════════════════════════
REGLAS DE FORMATO — NUNCA LAS VIOLES:
═══════════════════════════════════════════════════════════
REGLA 1 — FORMATO DE RESPUESTA:
Responde ÚNICAMENTE con un objeto JSON válido. Sin texto explicativo antes ni después. Sin bloques de marcado markdown como ```json o similares. Solo el JSON puro y directo.

REGLA 2 — ESTRUCTURA OBLIGATORIA DEL JSON:
El JSON debe tener EXACTAMENTE estas 3 claves principales de nivel superior:
  "calentamiento"
  "entrenamiento_principal"
  "estiramiento"

REGLA 3 — ESTRUCTURA DE CADA EJERCICIO:
Cada bloque contiene una lista de objetos. Cada ejercicio es un objeto con EXACTAMENTE estas 5 claves en minúsculas:
  "ejercicio"     → nombre real, específico y profesional del ejercicio (NUNCA genérico)
  "series"        → número de series como string (ej. "3" o "4")
  "repeticiones"  → rango o número de repeticiones (ej. "12-15", "6-8" o "12")
  "descanso"      → tiempo estimado (ej. "60 seg", "90 seg" o "2 min")
  "nota"          → tip breve enfocado en la ejecución técnica correcta y segura
"""

def _build_user_prompt(user_data: dict) -> str:
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
        # Inicialización del cliente leyendo desde settings.py
        api_key = getattr(settings, "GROQ_API_KEY", None)
        self.client = Groq(api_key=api_key) if api_key else None
        
        # Lee dinámicamente el modelo configurado en tu archivo .env
        self.model_name = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
        print(f"[BIO-FIT] Motor de IA cargado con el modelo: {self.model_name}")

    def generate_routine(self, user_data: dict) -> dict:
        """Genera una rutina de ejercicios adaptada con datos reales y específicos."""
        if not self.client:
            print("[BIO-FIT] ERROR: No se detectó GROQ_API_KEY en los settings.")
            return {'success': False, 'error': 'La API Key de Groq no está configurada.'}

        try:
            # Construcción dinámica del prompt con las selecciones del atleta
            user_msg = _build_user_prompt(user_data)

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                # Subimos ligeramente la temperatura a 0.75 para dar flexibilidad creativa
                # al diseño fitness sin perder la rigidez de la sintaxis JSON
                temperature=0.75,       
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
            print(f"[BIO-FIT] JSON inválido de Groq: {e}\nContenido original: {content[:500]}")
            return {'success': False, 'error': 'La IA devolvió un formato inesperado. Inténtalo de nuevo.'}
        except Exception as e:
            print(f"[BIO-FIT] Error crítico en módulo Groq: {e}")
            return {'success': False, 'error': f'Error de conexión con el motor de IA: {str(e)}'}

    def _limpiar_json(self, texto: str) -> str:
        """Limpia cualquier residuo de texto o markdown que pueda romper el parseo del JSON."""
        texto_limpio = texto.strip()
        # Elimina bloques de código markdown si la IA los agregó por error
        if texto_limpio.startswith("```json"):
            texto_limpio = texto_limpio[7:]
        elif texto_limpio.startswith("```"):
            texto_limpio = texto_limpio[3:]
        
        if texto_limpio.endswith("```"):
            texto_limpio = texto_limpio[:-3]
            
        return texto_limpio.strip()


# Instancia única reutilizable para toda la aplicación
routine_generator = RoutineGenerator()
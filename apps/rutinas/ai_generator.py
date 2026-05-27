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
diego
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
=======
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
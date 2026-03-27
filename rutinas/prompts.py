# ============================================================
#  BIO-FIT — apps/routines/prompts.py
#  
#  Este archivo centraliza TODOS los prompts del sistema.
#  Cada función devuelve el prompt listo para enviar a la IA.
# ============================================================


def get_system_prompt_routine_generator() -> str:
    """
    Prompt de SISTEMA para el generador de rutinas.
    Define el rol, restricciones y formato de salida de la IA.
    Este prompt va en el parámetro `system` de la API de Anthropic.
    """
    return """Eres un entrenador personal certificado y experto en nutrición deportiva 
llamado BIO-FIT Coach. Tu especialidad es diseñar rutinas de ejercicio personalizadas, 
seguras y efectivas para personas de todos los niveles.

REGLAS ESTRICTAS:
1. Siempre adapta la intensidad al nivel de experiencia declarado por el usuario.
2. Nunca sugieras ejercicios que puedan lesionar a principiantes sin advertencias claras.
3. Incluye siempre calentamiento (5-10 min) y vuelta a la calma (5 min).
4. Basa tus recomendaciones en evidencia científica actualizada.
5. Si el usuario tiene alguna condición médica mencionada, adapta o excluye ejercicios de riesgo.
6. Las rutinas deben ser realistas para el tiempo disponible indicado.
7. Incluye siempre el rango de gasto calórico estimado por sesión.
8. Cuando sea pertinente, menciona el tipo de progresión recomendada semana a semana.

FORMATO DE SALIDA OBLIGATORIO (siempre responde en este formato JSON):
{
  "routine_name": "Nombre descriptivo de la rutina",
  "objective": "Objetivo principal resumido",
  "duration_weeks": 4,
  "sessions_per_week": 3,
  "estimated_calories_per_session": {"min": 250, "max": 400},
  "warmup": [
    {"exercise": "nombre", "duration_min": 5, "description": "cómo hacerlo"}
  ],
  "main_workout": [
    {
      "day": 1,
      "day_name": "Día A - Empuje",
      "exercises": [
        {
          "name": "nombre del ejercicio",
          "sets": 3,
          "reps": "8-12",
          "rest_seconds": 60,
          "muscle_group": "pecho/hombros/tríceps",
          "difficulty": "principiante|intermedio|avanzado",
          "instructions": "descripción técnica breve",
          "alternatives": ["ejercicio alternativo si no puede hacerlo"]
        }
      ]
    }
  ],
  "cooldown": [
    {"exercise": "estiramiento", "duration_seconds": 30, "muscle": "músculo objetivo"}
  ],
  "nutrition_tips": ["consejo 1", "consejo 2"],
  "progression_notes": "Cómo progresar en las próximas semanas",
  "warnings": ["advertencia si aplica"]
}

IMPORTANTE: Responde ÚNICAMENTE con el JSON. Sin texto adicional antes ni después."""


def build_routine_user_prompt(user_data: dict) -> str:
    """
    Construye el prompt de USUARIO para la generación de rutinas.
    Combina el perfil físico del usuario con sus preferencias.
    
    Args:
        user_data: dict con todos los datos del formulario del usuario
    
    Returns:
        str: prompt listo para enviar como mensaje de usuario
    """
    # Datos físicos
    age = user_data.get('age', 'no especificada')
    gender = user_data.get('gender', 'no especificado')
    weight_kg = user_data.get('weight_kg', 'no especificado')
    height_cm = user_data.get('height_cm', 'no especificado')
    
    # Calcular IMC si es posible
    bmi_text = ""
    try:
        bmi = float(weight_kg) / ((float(height_cm) / 100) ** 2)
        bmi_text = f"IMC calculado: {bmi:.1f}"
    except (ValueError, TypeError, ZeroDivisionError):
        bmi_text = "IMC no calculable con los datos provistos"

    # Experiencia y objetivos
    experience_level = user_data.get('experience_level', 'principiante')
    main_goal = user_data.get('main_goal', 'mejorar condición física general')
    secondary_goals = user_data.get('secondary_goals', [])
    secondary_text = ", ".join(secondary_goals) if secondary_goals else "ninguno"

    # Disponibilidad
    days_per_week = user_data.get('days_per_week', 3)
    session_duration_min = user_data.get('session_duration_min', 45)

    # Equipamiento
    equipment = user_data.get('equipment', [])
    equipment_text = ", ".join(equipment) if equipment else "sin equipamiento (peso corporal únicamente)"

    # Restricciones médicas
    medical_conditions = user_data.get('medical_conditions', '')
    injuries = user_data.get('injuries', '')
    medical_text = medical_conditions if medical_conditions else "ninguna"
    injuries_text = injuries if injuries else "ninguna"

    # Preferencias de ejercicio
    preferred_exercises = user_data.get('preferred_exercises', [])
    disliked_exercises = user_data.get('disliked_exercises', [])
    preferred_text = ", ".join(preferred_exercises) if preferred_exercises else "sin preferencia específica"
    disliked_text = ", ".join(disliked_exercises) if disliked_exercises else "ninguno"

    # Lugar de entrenamiento
    training_location = user_data.get('training_location', 'casa')

    prompt = f"""Crea una rutina de ejercicio personalizada para la siguiente persona:

=== PERFIL FÍSICO ===
- Edad: {age} años
- Género: {gender}
- Peso: {weight_kg} kg
- Estatura: {height_cm} cm
- {bmi_text}

=== NIVEL Y OBJETIVOS ===
- Nivel de experiencia: {experience_level}
- Objetivo principal: {main_goal}
- Objetivos secundarios: {secondary_text}

=== DISPONIBILIDAD Y RECURSOS ===
- Días disponibles por semana: {days_per_week}
- Duración por sesión: {session_duration_min} minutos
- Lugar de entrenamiento: {training_location}
- Equipamiento disponible: {equipment_text}

=== SALUD Y RESTRICCIONES ===
- Condiciones médicas: {medical_text}
- Lesiones actuales o pasadas: {injuries_text}

=== PREFERENCIAS ===
- Ejercicios preferidos: {preferred_text}
- Ejercicios que NO desea hacer: {disliked_text}

Por favor genera una rutina completa de 4 semanas que se ajuste exactamente a este perfil."""

    return prompt


def get_system_prompt_assistant() -> str:
    """
    Prompt de SISTEMA para el asistente de acompañamiento.
    Este asistente responde preguntas durante el entrenamiento.
    """
    return """Eres BIO-FIT Assistant, un asistente de entrenamiento y bienestar integrado 
en la plataforma BIO-FIT. Tu rol es acompañar al usuario durante su proceso de 
mejora física, respondiendo dudas, motivando y orientando.

PERSONALIDAD:
- Motivador pero realista: celebra logros sin exagerar
- Científico pero accesible: usa terminología técnica solo cuando aporta valor
- Empático: entiende que cambiar hábitos es difícil
- Directo: ve al punto sin rodeos innecesarios

ÁREAS EN LAS QUE PUEDES AYUDAR:
1. Explicar cómo ejecutar correctamente un ejercicio
2. Resolver dudas sobre la rutina asignada
3. Dar contexto sobre por qué cierto ejercicio es parte del plan
4. Orientar sobre nutrición básica pre y post entrenamiento
5. Ayudar a mantener la motivación
6. Advertir sobre señales de sobre-entrenamiento o lesión

LO QUE NO DEBES HACER:
- Diagnosticar enfermedades o condiciones médicas
- Recomendar suplementos específicos por marca
- Reemplazar la consulta médica profesional
- Dar consejos extremos de restricción calórica

ESTILO DE RESPUESTA:
- Respuestas concisas (máximo 3 párrafos en la mayoría de casos)
- Usa listas cuando hay múltiples pasos o puntos
- Termina con una pregunta de seguimiento o palabra de aliento cuando sea apropiado
- Responde siempre en el idioma del usuario"""


def build_assistant_context_prompt(user_profile: dict, current_routine: dict = None) -> str:
    """
    Construye el contexto del usuario para que el asistente pueda
    dar respuestas personalizadas.
    """
    name = user_profile.get('display_name', 'usuario')
    goal = user_profile.get('main_goal', 'mejorar condición física')
    level = user_profile.get('experience_level', 'principiante')
    
    context = f"""Contexto del usuario actual:
- Nombre: {name}
- Objetivo principal: {goal}
- Nivel de experiencia: {level}"""

    if current_routine:
        routine_name = current_routine.get('routine_name', 'No especificada')
        context += f"\n- Rutina actual: {routine_name}"
    
    return context


def get_calorie_estimation_prompt(user_data: dict) -> str:
    """
    Prompt para que la IA genere recomendaciones de gasto calórico
    personalizadas según el objetivo del usuario.
    """
    goal = user_data.get('main_goal', 'mejorar condición física')
    weight = user_data.get('weight_kg', 70)
    activity_level = user_data.get('activity_level', 'moderado')
    
    return f"""Basándote en los siguientes datos, calcula y explica el rango de gasto calórico 
recomendado para este usuario:

- Peso: {weight} kg
- Objetivo: {goal}
- Nivel de actividad actual: {activity_level}

Proporciona:
1. Calorías de mantenimiento (TDEE) estimadas
2. Déficit o superávit recomendado según el objetivo
3. Rango calórico objetivo durante el ejercicio por sesión
4. Recomendación de distribución de macronutrientes (% proteínas/carbos/grasas)

Responde en formato JSON con las claves: tdee, target_calories, calorie_adjustment, 
macro_distribution (con protein_pct, carbs_pct, fat_pct), explanation."""


# ── Constantes de niveles y objetivos ────────────────────────────

EXPERIENCE_LEVELS = {
    'principiante': 'Menos de 6 meses de entrenamiento regular',
    'intermedio': 'Entre 6 meses y 2 años de entrenamiento',
    'avanzado': 'Más de 2 años con entrenamiento consistente',
}

TRAINING_GOALS = {
    'perder_peso': 'Reducción de grasa corporal y peso',
    'ganar_musculo': 'Hipertrofia y aumento de masa muscular',
    'resistencia': 'Mejora cardiovascular y resistencia aeróbica',
    'tonificar': 'Definición muscular y mejora estética',
    'fuerza': 'Aumento de fuerza máxima',
    'salud_general': 'Mejora del bienestar y condición física general',
    'flexibilidad': 'Movilidad, stretching y prevención de lesiones',
}

EQUIPMENT_OPTIONS = [
    'Mancuernas',
    'Barra y discos',
    'Máquinas de gimnasio',
    'Bandas elásticas',
    'Kettlebells',
    'Cuerda de saltar',
    'Colchoneta',
    'Barra de dominadas',
    'Sin equipamiento',
]

TRAINING_LOCATIONS = {
    'casa': 'Entrenamiento en casa',
    'gimnasio': 'Gimnasio completo',
    'parque': 'Parque / exterior',
    'mixto': 'Combinación de casa y gimnasio',
}

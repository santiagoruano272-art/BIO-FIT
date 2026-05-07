

import json
import logging
from django.conf import settings
import anthropic
from biofit.apps.calories.calculator import calcular_calorias_completas

from .prompts import (
    get_system_prompt_routine_generator,
    build_routine_user_prompt,
    get_calorie_estimation_prompt,
)

logger = logging.getLogger(__name__)


class RoutineGeneratorAI:
    """
    Clase principal para generar rutinas de ejercicio con IA.
    Encapsula toda la lógica de comunicación con la API de Anthropic.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL
        self.max_tokens = settings.ANTHROPIC_MAX_TOKENS

    def generate_routine(self, user_data: dict) -> dict:
        """
        Genera una rutina personalizada para el usuario.

        Args:
            user_data: dict con todos los datos del formulario del usuario
                Ejemplo:
                {
                    'age': 28,
                    'gender': 'masculino',
                    'weight_kg': 75,
                    'height_cm': 175,
                    'experience_level': 'principiante',
                    'main_goal': 'perder_peso',
                    'days_per_week': 3,
                    'session_duration_min': 45,
                    'equipment': ['Mancuernas', 'Colchoneta'],
                    'training_location': 'casa',
                    'medical_conditions': '',
                    'injuries': '',
                }

        Returns:
            dict con la rutina generada o un dict de error
        """
        try:
            system_prompt = get_system_prompt_routine_generator()
            user_prompt = build_routine_user_prompt(user_data)

            logger.info(f"Generando rutina para usuario con objetivo: {user_data.get('main_goal')}")

            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            response_text = message.content[0].text

            # Limpiar posibles backticks de markdown si la IA los añade
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            routine_data = json.loads(response_text.strip())

            logger.info(f"Rutina generada exitosamente: {routine_data.get('routine_name')}")
            return {
                'success': True,
                'routine': routine_data,
                'tokens_used': message.usage.input_tokens + message.usage.output_tokens,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de la IA: {e}")
            return {
                'success': False,
                'error': 'La IA devolvió un formato inesperado. Intenta de nuevo.',
                'raw_response': response_text if 'response_text' in locals() else '',
            }

        except anthropic.APIConnectionError:
            logger.error("Error de conexión con la API de Anthropic")
            return {
                'success': False,
                'error': 'No se pudo conectar con el servicio de IA. Verifica tu conexión.',
            }

        except anthropic.RateLimitError:
            logger.warning("Rate limit alcanzado en Anthropic API")
            return {
                'success': False,
                'error': 'Servicio temporalmente ocupado. Intenta en unos minutos.',
            }

        except anthropic.APIStatusError as e:
            logger.error(f"Error de API Anthropic: {e.status_code} — {e.message}")
            return {
                'success': False,
                'error': f'Error del servicio de IA: {e.message}',
            }

        except Exception as e:
            logger.exception(f"Error inesperado generando rutina: {e}")
            return {
                'success': False,
                'error': 'Ocurrió un error inesperado. Por favor contacta soporte.',
            }

    def estimate_calories(self, user_data: dict) -> dict:
        """
        Genera recomendaciones de gasto calórico personalizadas.
        """
        try:
            prompt = get_calorie_estimation_prompt(user_data)

            message = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text.strip()
            # Limpiar backticks
            for prefix in ("```json", "```"):
                if response_text.startswith(prefix):
                    response_text = response_text[len(prefix):]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            calorie_data = json.loads(response_text.strip())
            return {'success': True, 'data': calorie_data}

        except Exception as e:
            logger.exception(f"Error estimando calorías: {e}")
            return {'success': False, 'error': str(e)}


class AssistantAI:
    """
    Asistente conversacional de BIO-FIT.
    Mantiene el contexto de la conversación con historial.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL

    def chat(self, user_message: str, conversation_history: list,
             user_profile: dict, current_routine: dict = None) -> dict:
        """
        Envía un mensaje al asistente y obtiene la respuesta.

        Args:
            user_message: mensaje del usuario
            conversation_history: lista de mensajes previos
                Formato: [{"role": "user"|"assistant", "content": "..."}]
            user_profile: perfil del usuario para contextualizar
            current_routine: rutina actual del usuario (opcional)

        Returns:
            dict con 'success', 'response' y 'updated_history'
        """
        from .prompts import get_system_prompt_assistant, build_assistant_context_prompt

        try:
            context = build_assistant_context_prompt(user_profile, current_routine)
            system = get_system_prompt_assistant() + f"\n\n{context}"

            # Construir historial limitado (últimos 10 mensajes para no exceder tokens)
            limited_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            messages = limited_history + [{"role": "user", "content": user_message}]

            message = self.client.messages.create(
                model=self.model,
                max_tokens=600,
                system=system,
                messages=messages,
            )

            assistant_response = message.content[0].text

            # Actualizar historial
            updated_history = messages + [
                {"role": "assistant", "content": assistant_response}
            ]

            return {
                'success': True,
                'response': assistant_response,
                'updated_history': updated_history,
            }

        except Exception as e:
            logger.exception(f"Error en asistente IA: {e}")
            return {
                'success': False,
                'response': 'Lo siento, ocurrió un error. Por favor intenta de nuevo.',
                'updated_history': conversation_history,
            }


# ── Instancias singleton para reutilizar conexiones ──────────
routine_generator = RoutineGeneratorAI()
assistant_ai = AssistantAI()

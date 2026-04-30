import logging
import anthropic
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Inicializar cliente Anthropic 
_anthropic_client = None

def get_client() -> anthropic.Anthropic:
    """ 
    Retorna la instancia singleton del cliente Anthropic.
    Si no está inicializado, lo crea usando la API key de las variables de entorno."""
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no está definida en las variables de entorno")
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
        logger.info("Cliente Anthropic inicializado correctamente")
    return _anthropic_client


class AnthropicClient:
    """
    Encapsula todas las operaciones con la API de Anthropic.

    Responsabilidades:
    - Generación de rutinas de entrenamiento
    - Respuestas del asistente conversacional
    - Manejo de errores y logging centralizado
    """

    MODEL = "claude-3-5-haiku-20241022"  # Modelo actualizado
    MAX_TOKENS_RUTINA = 2048
    MAX_TOKENS_CHAT = 1024

    def __init__(self):
        self.client = get_client()

    # ── GENERACIÓN DE RUTINAS ────────────────────────────────

    def generar_rutina(self, user_inputs: dict) -> dict:
        """
        Genera una rutina de entrenamiento personalizada.

        Args:
            user_inputs: Datos del usuario (objetivo, nivel, días, etc.)

        Returns:
            dict con la rutina generada y metadatos
        """
        try:
            prompt = self._build_rutina_prompt(user_inputs)

            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS_RUTINA,
                system=(
                    "Eres un entrenador personal experto. "
                    "Genera rutinas de entrenamiento estructuradas, seguras y personalizadas. "
                    "Responde siempre en español y en formato JSON válido."
                ),
                messages=[{"role": "user", "content": prompt}],
            )

            rutina_text = response.content[0].text
            logger.info(f"Rutina generada exitosamente. Tokens usados: {response.usage.output_tokens}")

            return {
                "rutina_raw": rutina_text,
                "model": response.model,
                "tokens_usados": response.usage.output_tokens,
                "generada_en": datetime.utcnow().isoformat(),
            }

        except anthropic.AuthenticationError:
            logger.error("API key de Anthropic inválida")
            raise
        except anthropic.RateLimitError:
            logger.warning("Rate limit alcanzado en Anthropic")
            raise
        except anthropic.APIError as e:
            logger.error(f"Error de API Anthropic al generar rutina: {e}")
            raise

    # ── ASISTENTE CONVERSACIONAL ─────────────────────────────

    def generar_respuesta_chat(
        self,
        mensaje: str,
        historial: list[dict] | None = None,
        user_profile: dict | None = None,
    ) -> dict:
        """
        Genera una respuesta del asistente con soporte de historial.

        Args:
            mensaje:      Mensaje actual del usuario
            historial:    Lista de mensajes previos [{role, content}, ...]
            user_profile: Perfil del usuario para personalizar respuestas

        Returns:
            dict con la respuesta y metadatos
        """
        try:
            messages = (historial or []) + [{"role": "user", "content": mensaje}]

            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS_CHAT,
                system=self._build_system_prompt(user_profile),
                messages=messages,
            )

            respuesta = response.content[0].text
            logger.info(f"Respuesta de chat generada. Tokens: {response.usage.output_tokens}")

            return {
                "respuesta": respuesta,
                "tokens_usados": response.usage.output_tokens,
                "model": response.model,
            }

        except anthropic.APIError as e:
            logger.error(f"Error de API Anthropic en chat: {e}")
            raise

    # ── HELPERS PRIVADOS ─────────────────────────────────────

    def _build_rutina_prompt(self, user_inputs: dict) -> str:
        """Construye el prompt para generación de rutinas."""
        return (
            f"Crea una rutina de entrenamiento con los siguientes datos:\n"
            f"- Objetivo: {user_inputs.get('objetivo', 'no especificado')}\n"
            f"- Nivel: {user_inputs.get('nivel', 'principiante')}\n"
            f"- Días disponibles: {user_inputs.get('dias', 3)} por semana\n"
            f"- Duración por sesión: {user_inputs.get('duracion', 60)} minutos\n"
            f"- Equipamiento: {user_inputs.get('equipamiento', 'ninguno')}\n"
            f"- Restricciones físicas: {user_inputs.get('restricciones', 'ninguna')}\n"
        )

    def _build_system_prompt(self, user_profile: dict | None) -> str:
        """Construye el system prompt del asistente, personalizado si hay perfil."""
        base = (
            "Eres un asistente de fitness y bienestar experto. "
            "Responde siempre en español, de forma clara y motivadora."
        )
        if not user_profile:
            return base

        return (
            f"{base}\n\n"
            f"Contexto del usuario:\n"
            f"- Nombre: {user_profile.get('nombre', 'Usuario')}\n"
            f"- Objetivo: {user_profile.get('objetivo', 'no especificado')}\n"
            f"- Nivel: {user_profile.get('nivel', 'principiante')}\n"
        )
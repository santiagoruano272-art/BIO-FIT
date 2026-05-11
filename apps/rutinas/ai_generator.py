import json
from google import genai
from django.conf import settings
from .prompts import get_system_prompt_routine_generator, build_routine_user_prompt

class RoutineGeneratorAI:
    def __init__(self):
        # Forzamos la versión estable v1 en la conexión inicial
        self.client = genai.Client(
            api_key=settings.GOOGLE_API_KEY,
            http_options={'api_version': 'v1'}
        )

    def generate_routine(self, user_data: dict) -> dict:
        try:
            sys_instruct = get_system_prompt_routine_generator()
            user_msg = build_routine_user_prompt(user_data)
            
            # UNIFICACIÓN DE PROMPT:
            # Ponemos el rol del sistema y los datos en un solo bloque.
            # Esto evita que el SDK llame a endpoints beta de 'system_instruction'.
            full_content = (
                f"SISTEMA: {sys_instruct}\n\n"
                f"USUARIO: Genera una rutina basada en estos datos: {user_msg}\n"
                f"IMPORTANTE: Responde estrictamente en formato JSON."
            )
            
            response = self.client.models.generate_content(
                model="gemini-1.5-flash",
                contents=full_content,
                config={
                    "temperature": 0.7,
                    # Quitamos response_mime_type si el error 400 persiste
                }
            )

            if not response.text:
                return {'success': False, 'error': 'Respuesta vacía.'}

            # Limpiador de Markdown robusto
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()

            return {
                'success': True,
                'routine': json.loads(text)
            }
        except Exception as e:
            print(f"CRITICAL AI ERROR: {str(e)}")
            return {'success': False, 'error': str(e)}

routine_generator = RoutineGeneratorAI()
import json
from groq import Groq
from django.conf import settings
from .prompts import get_system_prompt_routine_generator, build_routine_user_prompt

class RoutineGeneratorAI:
    def __init__(self):
        """
        Inicializa el cliente de Groq utilizando la API Key de settings.py.
        """
        # Se asegura de usar la clave gsk_ configurada en tu .env 
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        
        # Usamos el modelo Llama 3.1 que es la versión actual soportada 
        # Si no se encuentra en settings, usamos 'llama-3.1-8b-instant' por defecto
        self.model_name = getattr(settings, 'GROQ_MODEL', 'llama-3.1-8b-instant')

    def generate_routine(self, user_data: dict) -> dict:
        """
        Genera una rutina de ejercicios enviando los datos del usuario a Groq.
        """
        try:
            # Obtención de instrucciones de sistema y datos del usuario desde prompts.py
            sys_instruct = get_system_prompt_routine_generator()
            user_msg = build_routine_user_prompt(user_data)
            
            # Llamada oficial a la API de Groq
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": sys_instruct},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.7,
                # Force la respuesta en formato JSON para BIO-FIT
                response_format={"type": "json_object"}
            )

            # Extraemos el contenido de la respuesta
            content = response.choices[0].message.content
            
            if not content:
                return {'success': False, 'error': 'Groq no devolvió contenido.'}

            # Retornamos el JSON parseado directamente para la vista
            return {
                'success': True,
                'routine': json.loads(content)
            }
            
        except Exception as e:
            # Registro del error en la terminal de Django para depuración 
            print(f"ERROR EN GROQ BIO-FIT: {str(e)}")
            return {
                'success': False, 
                'error': f"Error en el generador de IA: {str(e)}"
            }

# Instancia única para ser importada en las vistas de la aplicación
routine_generator = RoutineGeneratorAI()
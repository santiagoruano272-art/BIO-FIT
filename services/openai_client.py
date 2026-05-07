import openai
from django.conf import settings

class OpenAIClient:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY

    def generar_respuesta(self, prompt, context=""):
        response = openai.ChatCompletion.create(
            model="gpt-4", # o gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "Eres un experto en fitness y nutrición de BIO-FIT."},
                {"role": "user", "content": f"{context}\n\n{prompt}"}
            ]
        )
        return response.choices[0].message.content
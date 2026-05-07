from django.apps import AppConfig

class BiofitConfig(AppConfig):
    name = 'apps'

    def ready(self):
        # Aquí disparas la lógica inicial
        print("Servidor BIO-FIT iniciado. Verificando Endpoints de IA...")
        # Puedes importar aquí tus servicios para evitar importaciones circulares
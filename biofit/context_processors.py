from django.conf import settings

def firebase_config(request):
    return {
        'FIREBASE_API_KEY': settings.FIREBASE_API_KEY
    }

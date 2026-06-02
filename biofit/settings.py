import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ── SEGURIDAD ──
SECRET_KEY    = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-default-key')
DEBUG         = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ── APLICACIONES ──
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'apps.users',
    'apps.conexion',
    'apps.rutinas',
    'apps.asistente',
    'apps.calories',
    'apps.inventory',
]

# ── MIDDLEWARE ──
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'biofit.urls_app'

# ── TEMPLATES ──
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'biofit.wsgi.application'

# ── BASE DE DATOS ──
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME':   BASE_DIR / 'db.sqlite3',
    }
}

# ── SESIONES ──────────────────────────────────────────────────────────────────
# CRÍTICO: sin estas configuraciones la sesión se destruye entre navegaciones
# y el admin es redirigido al login aunque ya esté autenticado.
SESSION_ENGINE             = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE         = 86400   # 24 horas (en segundos)
SESSION_SAVE_EVERY_REQUEST = True    # renueva la sesión en cada request
SESSION_COOKIE_HTTPONLY    = True    # protección XSS
SESSION_COOKIE_SAMESITE    = 'Lax'  # compatibilidad con navegación interna
SESSION_COOKIE_SECURE      = False   # cambiar a True en producción (HTTPS)
# ─────────────────────────────────────────────────────────────────────────────

# ── ARCHIVOS ESTÁTICOS (CSS, JS, IMÁGENES) ──
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'biofit' / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

# ── GROQ CLOUD (IA) ──
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL   = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')

# ── FIREBASE ──
FIREBASE_API_KEY             = os.getenv('FIREBASE_API_KEY')
FIREBASE_CREDENTIALS_PATH    = os.path.join(BASE_DIR, 'bio-fit-serviceAccountKey.json')

# ── LOCALIZACIÓN ──
LANGUAGE_CODE = 'es-co'
TIME_ZONE     = 'America/Bogota'
USE_I18N      = True
USE_TZ        = True

# ── OTROS ──
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── REDIRECCIONES DE AUTENTICACIÓN ──
LOGIN_URL          = 'login-page'
LOGIN_REDIRECT_URL = 'landing'
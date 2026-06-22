from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'data' / 'timestamper_database',
    }
}


CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://192.168.0.127:5173"
]


ALLOWED_HOSTS = ['192.168.0.127', 'localhost', '127.0.0.1']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'test@deine-app.local'
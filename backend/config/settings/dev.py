from .base import *


DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1")


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


ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost").split(",")


SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(hours=6)
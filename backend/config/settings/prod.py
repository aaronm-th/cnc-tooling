import os
from datetime import timedelta
from .base import *

# ----------------------------------------------------------------------
# Sicherheit & Hosting-Infrastruktur
# ----------------------------------------------------------------------
DEBUG = False

# Wird über Docker-Umgebungsvariablen gesetzt (z.B. "192.168.0.200,mein-mini-pc.local")
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Proxy-Einstellungen (wichtig, da Nginx vor Django geschaltet ist)
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Da der Zugriff im Heimnetzwerk oft über http:// (Port 80) läuft:
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "0") == "1"
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "0") == "1"


# ----------------------------------------------------------------------
# PostgreSQL Datenbank-Konfiguration
# ----------------------------------------------------------------------
# Hinweis: Das 'psycopg2-binary'-Paket muss in deinen Python-Requirements sein!
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get("POSTGRES_DB", "urlaubsplaner_db"),
        'USER': os.environ.get("POSTGRES_USER", "postgres"),
        'PASSWORD': os.environ.get("POSTGRES_PASSWORD"),
        'HOST': os.environ.get("POSTGRES_HOST", "db"),  # "db" entspricht dem Servicenamen in docker-compose
        'PORT': os.environ.get("POSTGRES_PORT", "5432"),
    }
}


# ----------------------------------------------------------------------
# CORS & CSRF (Schnittstelle zum Vue Frontend)
# ----------------------------------------------------------------------
# Erlaubt dem Vue-Frontend den Zugriff auf die API
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")



# ----------------------------------------------------------------------
# Statische Dateien & Logging
# ----------------------------------------------------------------------
# In der Produktion sammeln wir alle statischen Dateien in diesem Ordner,
# damit Nginx sie direkt abgreifen und ausliefern kann.
STATIC_ROOT = os.environ.get("STATIC_ROOT", BASE_DIR / "staticfiles")
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", BASE_DIR / "media")

# Einfaches, robustes Konsolen-Logging für Docker-Logs
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
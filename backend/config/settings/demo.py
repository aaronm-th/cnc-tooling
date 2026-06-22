from .base import *

# Proxy-Einstellungen für Nginx
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Da du aktuell nur über Port 80 (HTTP) auf dem Mini-PC fährst:
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Datenbank für Produktion (hier deine DB-Logik einfügen)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Oder Postgres falls gewünscht
        'NAME': BASE_DIR / 'data' / 'timestamper_database',
    }
}
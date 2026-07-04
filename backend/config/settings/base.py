# config/settings/base.py

from pathlib import Path
import os
from datetime import timedelta
from celery.schedules import crontab



# --------------------
# Core
# --------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "_sw0sF66npeJpo9oamnZ_j76GiDVozTCIiK_S10xosY")
DEBUG = os.environ.get("DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "http://localhost").split(",")


# --------------------
# Applications
# --------------------

INSTALLED_APPS = [
    'event_calendar.apps.EventCalendarConfig',
    'management.apps.ManagementConfig',
    'attendance.apps.AttendanceConfig',
    'core.apps.CoreConfig',
    'reports.apps.ReportsConfig',
    'terminal.apps.TerminalConfig',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_celery_beat',
    'django_filters',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
]


# --------------------
# Middleware
# --------------------

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_CREDENTIALS = True


# --------------------
# URLs / Templates
# --------------------

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
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

WSGI_APPLICATION = 'config.wsgi.application'





# --------------------
# Auth / User
# --------------------

AUTH_USER_MODEL = 'core.Employee'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LOGIN_REDIRECT_URL = 'home'
LOGIN_URL = 'login'


# --------------------
# I18N
# --------------------

LANGUAGE_CODE = 'de-de'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True


# --------------------
# Static / Media
# --------------------

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"


# --------------------
# Messages
# --------------------

from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}


# --------------------
# Sessions
# --------------------

SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True


# --------------------
# REST Framework
# --------------------

REST_FRAMEWORK = {

    'DEFAULT_PERMISSION_CLASSES': [
        # Standardmäßig müssen User eingeloggt sein
        'rest_framework.permissions.IsAuthenticated',
    ],
    
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # WICHTIG: SimpleJWT für Vue hinzufügen
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # Beibehalten für den Django-Admin und lokales Browsen der API
        'rest_framework.authentication.SessionAuthentication',
    ],

    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Urlaubsplaner API',
    'DESCRIPTION': 'API zur Verwaltung von Urlaubsanträgen und Kalenderereignissen',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # Falls du JWT nutzt:
    'COMPONENT_SPLIT_PATCH': True,

    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SECURITY': [{
        'jwtAuth': [],
    }],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'jwtAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },
}


# --------------------
# SimpleJWT
# --------------------

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# --------------------
# Celery
# --------------------

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

broker_connection_retry_on_startup = True

CELERY_BEAT_SCHEDULE = {
    'auto-checkout-every-5-minutes': {
        'task': 'attendance.tasks.auto_checkout',
        'schedule': timedelta(minutes=5),
    },
    'create-workdays-at-midnight': {
        'task': 'attendance.tasks.generate_workdays_for_range',
        'schedule': crontab(hour=0, minute=5),
    }
}


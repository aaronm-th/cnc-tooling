import os
from celery import Celery
import logging
from celery.signals import after_setup_logger


@after_setup_logger.connect
def setup_log_format(logger, *args, **kwargs):
    # Das Format: [Datum/Uhrzeit] Nachricht
    formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='[%Y-%m-%d %H:%M:%S]')
    
    # Bestehende Handler überschreiben
    for handler in logger.handlers:
        handler.setFormatter(formatter)


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.demo')
app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
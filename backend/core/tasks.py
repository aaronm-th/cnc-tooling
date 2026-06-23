# your_app/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import Employee
from dateutil.relativedelta import relativedelta
from datetime import timedelta



@shared_task
def cleanup_old_notifications():
    from .models import Notification
    from django.utils import timezone
    limit = timezone.now() - timedelta(days=30)
    Notification.objects.filter(created_at__lt=limit, read=True).delete()
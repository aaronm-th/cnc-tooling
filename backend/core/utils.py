import os
import uuid
from django.utils.text import slugify

def user_profile_photo_upload(instance, filename):
    ext = filename.split('.')[-1]
    username_slug = slugify(instance.get_full_name())
    filename = f"{username_slug}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('profile_pics', filename)


# core/utils.py

def create_notifications_for_multiple_users(recipients, title, message, notification_type='info', link_to=None, content_object=None):
    from .models import Notification
    
    notifications = [
        Notification(
            recipient=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link_to=link_to,
            content_object=content_object  # <-- Hier wird das Django-Objekt übergeben
        )
        for user in recipients
    ]
    
    return Notification.objects.bulk_create(notifications)


def create_notification(user, title, message, notification_type='info', link_to=None, content_object=None):
    created_notifications = create_notifications_for_multiple_users(
        recipients=[user],
        title=title,
        message=message,
        notification_type=notification_type,
        link_to=link_to,
        content_object=content_object  # <-- Weiterleitung
    )
    return created_notifications[0] if created_notifications else None
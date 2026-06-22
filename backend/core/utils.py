
import os
import uuid
from django.utils.text import slugify


def user_profile_photo_upload(instance, filename):
    # Get file extension
    ext = filename.split('.')[-1]

    # Optional: slugify username to make it URL-safe
    username_slug = slugify(instance.get_full_name())

    # Build new filename
    filename = f"{username_slug}_{uuid.uuid4().hex[:8]}.{ext}"

    # Final path: profile_pics/username_xyz12345.jpg
    return os.path.join('profile_pics', filename)





def create_notification(user, title, message, notification_type='info', link_to=None, reference_id=None):
    from .models import Notification
    return Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link_to=link_to,
        reference_id=reference_id  # Hier die ID speichern
    )
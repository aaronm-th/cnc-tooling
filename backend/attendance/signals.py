from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import WSChangeRequest

@receiver(post_delete, sender=WSChangeRequest)
def remove_notification_on_delete(sender, instance, **kwargs):
    """
    Wird aufgerufen, wenn ein Änderungsantrag gelöscht wird.
    Sucht die zugehörigen Benachrichtigungen via ContentType und löscht sie.
    """
    from core.models import Notification
    
    # 1. Hol den Typen des gelöschten Models (WSChangeRequest)
    ct = ContentType.objects.get_for_model(instance)
    
    # 2. Lösche alle Benachrichtigungen, die diesen Typ und diese Objekt-ID hatten
    Notification.objects.filter(content_type=ct, object_id=instance.id).delete()
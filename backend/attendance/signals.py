from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import WSChangeRequest
from core.models import Notification

@receiver(post_delete, sender=WSChangeRequest)
def remove_notification_on_delete(sender, instance, **kwargs):
    """
    Wird aufgerufen, wenn ein Änderungsantrag gelöscht wird.
    Sucht die zugehörige Benachrichtigung und löscht sie.
    """
    ref = f"wscreq_{instance.id}"
    # Wir löschen die Nachricht beim Supervisor
    Notification.objects.filter(reference_id=ref).delete()
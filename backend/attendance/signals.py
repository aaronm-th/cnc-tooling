from django.db.models.signals import post_delete
from django.db.models.signals import pre_save
from django.dispatch import receiver

from django.contrib.contenttypes.models import ContentType

from .models import WSChangeRequest, WorkDay

import holidays

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


# --- 2. Automatische Klassifizierung von Arbeitstagen (Wochenende/Feiertag) ---
@receiver(pre_save, sender=WorkDay)
def auto_classify_day(sender, instance, **kwargs):
    """
    Weist dem WorkDay automatisch den passenden Typ zu (Wochenende oder Feiertag),
    sofern der Tag nicht manuell überschrieben wurde.
    """
    if instance.date and instance.day_type == WorkDay.DayType.WORK:
        de_holidays = holidays.Germany(subdiv='BW', years=instance.date.year)
        
        # 1. Feiertage prüfen
        if instance.date in de_holidays:
            instance.day_type = WorkDay.DayType.HOLIDAY
        
        # 2. Wochenenden prüfen (Samstag=5, Sonntag=6)
        elif instance.date.weekday() >= 5:
            # instance.sessions.exists() darf erst abgefragt werden, wenn die
            # Instanz eine pk hat (pre_save kann auch VOR dem ersten Insert
            # feuern). Ein neuer WorkDay kann ohnehin noch keine Sessions
            # haben, daher zählt das hier als "keine Sessions vorhanden".
            has_sessions = instance.pk is not None and instance.sessions.exists()
            if not has_sessions:
                instance.day_type = WorkDay.DayType.WEEKEND
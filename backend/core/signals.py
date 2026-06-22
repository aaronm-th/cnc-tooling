from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
import holidays

from .models import Employee, VacationQuota
from attendance.models import WorkDay

# --- 1. Altes Profilbild beim Aktualisieren löschen ---
@receiver(pre_save, sender=Employee)
def delete_old_photo_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_photo = sender.objects.get(pk=instance.pk).photo
    except sender.DoesNotExist:
        return

    if old_photo and old_photo.name != 'profile_photos/default.jpg':
        if instance.photo and old_photo.name != instance.photo.name:
            if old_photo.storage.exists(old_photo.name):
                old_photo.delete(save=False)


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
            instance.day_type = WorkDay.DayType.WEEKEND


# --- 3. Urlaubsanspruch für das aktuelle Jahr initialisieren ---
@receiver(post_save, sender=Employee)
def create_employee_vacation_quota(sender, instance, created, **kwargs):
    if created:
        current_year = timezone.now().year
        quota_days = instance.calculate_initial_quota(current_year)
        
        VacationQuota.objects.create(
            employee=instance,
            year=current_year,
            total_days=quota_days
        )
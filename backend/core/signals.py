from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


from .models import Employee

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



# --- 3. Urlaubsanspruch für das aktuelle Jahr initialisieren ---
@receiver(post_save, sender=Employee)
def create_employee_vacation_quota(sender, instance, created, **kwargs):
    if created and instance.joined_at:
        from core.services.vacation_service import VacationService
        from decimal import Decimal
        from core.models import VacationQuota
        
        target_year = instance.joined_at.year
        
        # Nutzen der neuen, existierenden Service-Methode
        allocated_days = VacationService.get_total_days_for_year(instance, target_year)
        
        VacationQuota.objects.get_or_create(
            employee=instance,
            year=target_year,
            defaults={
                'total_days': Decimal(str(allocated_days)),
                'carried_over': Decimal('0.0')
            }
        )
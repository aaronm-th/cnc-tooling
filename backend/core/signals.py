from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Employee, VacationQuota
from attendance.models import WorkDay
import holidays
from django.contrib.auth.models import Group
from django.utils import timezone

@receiver(pre_save, sender=Employee)
def delete_old_photo_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_photo = sender.objects.get(pk=instance.pk).photo
    except sender.DoesNotExist:
        return

    if old_photo and old_photo.name != 'profile_pics/default_profile.jpg':
        if instance.photo and old_photo.name != instance.photo.name:
            if old_photo.storage.exists(old_photo.name):
                old_photo.delete(save=False)

de_holidays = holidays.Germany(state='BW')

@receiver(pre_save, sender=WorkDay)
def auto_classify_day(sender, instance, **kwargs):
    """
    Automatically assigns DayType based on date.
    Only triggers if the user hasn't manually changed it from 'work'.
    """
    if instance.date and instance.day_type == WorkDay.DayType.WORK:
        # 1. Check Public Holidays first
        if instance.date in de_holidays:
            instance.day_type = WorkDay.DayType.HOLIDAY
        
        # 2. Check Weekends (Saturday=5, Sunday=6)
        elif instance.date.weekday() >= 5:
            instance.day_type = WorkDay.DayType.WEEKEND




@receiver(post_save, sender=Employee)
def assign_default_group(sender, instance, created, **kwargs):
    if created:
        # 1. Look for the 'Employee' group
        group, _ = Group.objects.get_or_create(name='Mitarbeiter')
        # 2. Add the user to it
        instance.groups.add(group)


@receiver(post_save, sender=Employee)
def create_employee_vacation_quota(sender, instance, created, **kwargs):
    if created:
        current_year = timezone.now().year
        # Berechne Initialanspruch basierend auf Eintrittsdatum
        quota_days = instance.calculate_initial_quota(current_year)
        
        VacationQuota.objects.create(
            employee=instance,
            year=current_year,
            total_days=quota_days
        )



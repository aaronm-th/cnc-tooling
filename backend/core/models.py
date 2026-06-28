import datetime
import holidays
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from .utils import user_profile_photo_upload

class Employee(AbstractUser):
    # E-Mail wird optional, da Offline-Betrieb
    email = models.EmailField(blank=True, null=True, unique=False)
    phone = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to=user_profile_photo_upload, blank=True, null=True)
    work_days_schema = models.JSONField(
        default=dict, 
        help_text="Format: {'0': 8, '1': 8...} (0=Mo, 6=So). Fehlt ein Tag, gilt hours_per_day als Fallback für Werktage."
    )
    
    joined_at = models.DateField(default=timezone.now)
    vacation_days_per_year = models.DecimalField(max_digits=5, decimal_places=2, default=30.0)

    @property
    def weekly_hours(self) -> float:
        """
        Berechnet die wöchentliche Sollarbeitszeit dynamisch aus dem work_days_schema.
        Fehlen Tage im Schema komplett, fallen Werktage (Mo-Fr) auf ein Standard-Soll von 8.0 Std zurück.
        """
        total = 0.0
        # Wir loopen über alle Wochentage (0=Mo bis 6=So)
        for i in range(7):
            weekday_key = str(i)
            if weekday_key in self.work_days_schema:
                total += float(self.work_days_schema[weekday_key])
            elif i < 5:
                # Fallback für Werktage, falls das Schema für diesen Tag unvollständig ist
                total += 8.0
        return round(total, 2)

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def initials(self) -> str:
        initials = (self.first_name[:1] + self.last_name[:1]).upper()
        return initials if initials.strip() else self.username[:2].upper()

    @property
    def status(self) -> bool:
        # Prüfen, ob es für diesen Mitarbeiter eine offene WorkSession gibt
        from attendance.models import WorkSession
        return WorkSession.objects.filter(
            work_day__employee=self,
            check_out__isnull=True
        ).exists()


    def is_holiday(self, date_obj):
        de_holidays = holidays.Germany(subdiv='BW', years=date_obj.year)
        return date_obj in de_holidays

    def is_absent(self, date_obj):
        from attendance.models import LeaveRequest
        return LeaveRequest.objects.filter(
            employee=self,
            leave_start__lte=date_obj,
            leave_end__gte=date_obj,
            status='approved'
        ).exists()
    
    def get_expected_hours_for_date(self, date_obj):
    # NEU: Prüfen, ob für dieses Datum bereits ein manueller Urlaubs-/Krankheitstag existiert
        from attendance.models import WorkDay
        db_day = WorkDay.objects.filter(employee=self, date=date_obj).first()
        if db_day and db_day.day_type in [WorkDay.DayType.VACATION, WorkDay.DayType.SICK]:
            return 0.0

        # Deine bestehenden Urlaubsantrags- und Feiertags-Prüfungen
        if self.is_holiday(date_obj) or self.is_absent(date_obj):
            return 0.0

        weekday_key = str(date_obj.weekday())
        if weekday_key in self.work_days_schema:
            return float(self.work_days_schema[weekday_key])
        
        if date_obj.weekday() < 5:
            return float(self.hours_per_day)
    
        return 0.0

    def save(self, *args, **kwargs):
        # Automatische Username-Generierung beim ersten Speichern
        if not self.pk:
            # Falls die View bereits einen Usernamen übergeben hat (z.B. E-Mail o.ä.), 
            # generieren wir nur dann einen, wenn noch keiner gesetzt ist oder er 'admin' o.ä. kollidiert.
            if not self.username and self.last_name:
                # Umlaut-Ersetzung vor dem Slugify, um 'müller' -> 'mueller' zu machen
                clean_last_name = self.last_name.lower().replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
                base_username = slugify(clean_last_name)
                
                if not base_username:
                    base_username = slugify(self.first_name) or "user"
                    
                username = base_username
                counter = 1  
                

                while Employee.objects.filter(username=username).exists():

                    username = f"{base_username}{counter}"
                    counter += 1
                    
                self.username = username
            
            # WICHTIG: Das Initialpasswort entspricht EXAKT dem finalen Usernamen
            if self.username and not self.password:
                self.set_password(self.username)

        super().save(*args, **kwargs)

    @property
    def overtime_balance(self) -> float:
        """
        Berechnet das aktuelle Überstundenkonto des Mitarbeiters live.
        Geleistete Ist-Stunden abzüglich der vertraglichen Soll-Stunden.
        Der Chef (Superuser) hat standardmäßig immer 0.0.
        """
        # Wenn der Mitarbeiter der Chef (Superuser) ist, sammelt er keine Überstunden
        if self.is_superuser:
            return 0.0

        from attendance.models import WorkDay
        
        # 1. Alle Ist-Stunden summieren, die der Mitarbeiter je gearbeitet hat
        # (Nutzt das 'total_hours' Property vom WorkDay)
        workdays = WorkDay.objects.filter(employee=self)
        total_worked_hours = sum(day.total_hours for day in workdays)

        # 2. Alle Soll-Stunden für diese Tage berechnen
        total_expected_hours = sum(self.get_expected_hours_for_date(day.date) for day in workdays)

        # 3. Die Differenz ist das Überstundenkonto
        balance = total_worked_hours - total_expected_hours
        return round(balance, 2)


class VacationQuota(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='vacation_quotas')
    year = models.PositiveIntegerField()
    total_days = models.DecimalField(max_digits=5, decimal_places=2)
    carried_over = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    class Meta:
        unique_together = ('employee', 'year')



class Notification(models.Model):
    recipient = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, default='info')
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link_to = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Benachrichtigung für {self.recipient.username} - {self.title}"


class Scratchpad(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='scratchpad')
    content = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notizfeld"
        verbose_name_plural = "Notizfelder"

    def __str__(self):
        return f"Notizblock von {self.employee.name}"


class TodoItem(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='todos')
    text = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Todo für {self.employee.username}: {self.text[:20]}"
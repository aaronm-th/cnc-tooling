import datetime
import calendar

from django.contrib.auth.models import AbstractUser
from django.db import models

from .utils import user_profile_photo_upload
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .services.vacation_service import VacationService
from .services.overtime_service import OvertimeService

import uuid


class Invitation(models.Model):

    # Verknüpfung zum neu angelegten User (der noch inaktiv ist)
    employee = models.OneToOneField(
            settings.AUTH_USER_MODEL, 
            on_delete=models.CASCADE, 
            related_name='invitation'
        )    
    
    # Generiert automatisch eine unerratbare, lange ID (z.B. 4f3b8a12-...)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    # Einladung ist standardmäßig 48 Stunden gültig
    expires_at = models.DateTimeField()
    
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=48)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"Einladung für {self.employee.email} (Gültig: {self.is_valid})"


class Department(models.Model):
    name = models.CharField(max_length=100)
    # Der Kopf der Abteilung (optional)

    def __str__(self):
        return self.name

    def get_members_list(self):
            """Gibt ein QuerySet aller Mitarbeiter dieser Abteilung zurück"""
            return self.members.all()

    @property
    def member_count(self):
        """Gibt die Anzahl der Mitarbeiter zurück"""
        return self.members.count()

class Employee(AbstractUser):

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    photo = models.ImageField(
        upload_to=user_profile_photo_upload,
        blank=True,
        default=None
        )

    hours_per_day = models.FloatField(default=8.0)    
    work_days_schema = models.JSONField(default=dict, help_text="Format: {'0': 8, '1': 8...} (0=Mo, 6=So). Fehlt ein Tag, wird default_daily_hours genutzt.")
    joined_at = models.DateField(default=timezone.now)
    vacation_days_per_year = models.DecimalField(max_digits=5, decimal_places=2, default=30.0)
    supervisor = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subordinates'
    )

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def initials(self) -> str:
        return (f"{self.first_name[0] if self.first_name else ''}"
                f"{self.last_name[0] if self.last_name else ''}").upper() or "??"

    @property
    def is_supervisor(self) -> bool:
        return self.subordinates.exists()


    @property
    def overtime_balance(self):
        return OvertimeService.calculate_balance(self)

    def calculate_initial_quota(self, year):
        return VacationService.calculate_initial_quota(self, year)
    

    @property
    def status(self) -> bool:
        # Prüfen, ob es für diesen Mitarbeiter eine offene WorkSession gibt
        from attendance.models import WorkSession
        return WorkSession.objects.filter(
            work_day__employee=self,
            check_out__isnull=True
        ).exists()
    
    def is_holiday(self, date_obj):
        """
        Prüft, ob das Datum ein gesetzlicher Feiertage ist.
        Nutzt die 'holidays' Bibliothek. Falls nicht installiert: pip install holidays
        """
        import holidays
        # Erstellt den Feiertagskalender für das aktuelle Jahr (Beispiel NRW/Deutschland)
        de_holidays = holidays.Germany(subdiv='BW', years=date_obj.year)
        return date_obj in de_holidays


    def is_absent(self, date_obj):
        """
        Prüft, ob für den Mitarbeiter ein genehmigter Urlaub oder 
        ein Krankheitstag an diesem Datum existiert.
        """
        # Passe hier 'attendance.models' und 'LeaveRequest' an deine echte Struktur an!
        from attendance.models import LeaveRequest 
        
        return LeaveRequest.objects.filter(
            employee=self,
            leave_start__lte=date_obj,
            leave_end__gte=date_obj,
            status='approved' # Oder wie auch immer dein Status für "genehmigt/aktiv" heißt
        ).exists()
    
    def get_total_weekly_hours(self):
        """
        Berechnet die wöchentliche Sollsperre basierend auf dem Schema.
        Berücksichtigt Mo-Fr (0-4), außer das Schema definiert Sa/So explizit.
        """
        total = 0.0
        # Wir gehen die Standard-Arbeitstage durch (0=Mo bis 4=Fr)
        # Wenn du Sa/So (5, 6) auch standardmäßig einbeziehen willst, range(7)
        for day_index in range(5): 
            day_key = str(day_index)
            
            if day_key in self.work_days_schema:
                # Wert aus dem JSON nehmen (z.B. 4 oder 8.5)
                total += float(self.work_days_schema[day_key])
            else:
                # Fallback auf Standardstunden
                total += float(self.hours_per_day)
        
        # Prüfung auf Wochenende (Sa/So), falls diese im JSON stehen
        for weekend_index in [5, 6]:
            weekend_key = str(weekend_index)
            if weekend_key in self.work_days_schema:
                total += float(self.work_days_schema[weekend_key])
                
        return total

    # Optional: Als Property, damit du es wie ein Feld aufrufen kannst: employee.weekly_hours
    @property
    def weekly_hours(self):
        return self.get_total_weekly_hours()

    def get_expected_hours(self, date_obj):
        return self.get_expected_hours_for_date(date_obj)

    def get_expected_hours_for_date(self, date_obj):
        """
        Gibt die Soll-Stunden für ein bestimmtes Datum zurück.
        Berücksichtigt jetzt Feiertage, Urlaub und Krankheit (Soll = 0).
        """
        # 1. Prüfung auf Abwesenheiten & Feiertage (Early Exit)
        if self.is_holiday(date_obj) or self.is_absent(date_obj):
            return 0.0

        # 2. Schau im regulären JSON-Schema nach
        weekday_key = str(date_obj.weekday()) # "0" bis "6"
        if weekday_key in self.work_days_schema:
            return float(self.work_days_schema[weekday_key])
        
        # 3. Fallback: Wenn Tag im Schema fehlt, aber es ein Werktag ist (Mo-Fr)
        if date_obj.weekday() < 5:
            return float(self.hours_per_day)
        
        # 4. Wochenende (Sa/So) ohne Eintrag im Schema = 0 Stunden
        return 0.0


    def get_photo_url(self):
        if self.photo and hasattr(self.photo, 'url'):
            return f"http://localhost:8000{self.photo.url}"    
        return None


    def __str__(self):
        return f"{self.first_name} {self.last_name}"   
    
    
    def save(self, *args, **kwargs):
        # Bevor gespeichert wird: Username = Email
        self.username = self.email
        super().save(*args, **kwargs)
    

    def recalculate_snapshots(self, from_year, from_month):
        """
        Löscht Snapshots ab einem Datum und berechnet sie neu.
        Nützlich bei rückwirkenden Korrekturen.
        """
        self.monthly_balances.filter(
            models.Q(year__gt=from_year) | 
            models.Q(year=from_year, month__gte=from_month)
        ).delete()


class VacationQuota(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='vacation_quotas')
    year = models.PositiveIntegerField()
    
    # Jetzt als DecimalField, passend zum Employee-Modell!
    total_days = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text="Individueller Anspruch für dieses spezifische Jahr. Falls leer, greift der Vertragswert."
    )
    carried_over = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    carry_over_expiry = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('employee', 'year')

    @classmethod
    def carry_over_to_next_year(cls, employee, current_year):
        old_quota = cls.objects.filter(employee=employee, year=current_year).first()
        remaining = old_quota.remaining_days if old_quota else 0
        
        new_year = current_year + 1
        
        # Hier nutzen wir den Vertragswert des Employees NUR als Standardwert (Default)
        new_quota, created = cls.objects.get_or_create(
            employee=employee,
            year=new_year,
            defaults={
                'total_days': employee.vacation_days_per_year, # Vertragswert als Basis für das neue Jahr
                'carried_over': remaining,
                'carry_over_expiry': datetime.date(new_year, 3, 31)
            }
        )
        return new_quota

    @classmethod
    def create_for_employee(cls, employee, year):
        """Erstellt das offizielle Jahres-Kontingent unter Nutzung des Services"""
        # Berechne den initialen Anspruch (berücksichtigt anteiliges Jahr)
        allocated_days = VacationService.calculate_initial_quota(employee, year)
        
        return cls.objects.create(
            employee=employee,
            year=year,
            total_days=allocated_days,
            carried_over=0.0
        )

    @property
    def total_available_days(self):
        """Die Gesamtzahl an Urlaubstagen, die dieses Jahr genommen werden können."""
        return self.total_days + self.carried_over
    


class MonthlyBalance(models.Model):
    employee = models.ForeignKey(
        'core.Employee', 
        on_delete=models.CASCADE, 
        related_name='monthly_balances'
    )
    month = models.PositiveIntegerField()  # 1-12
    year = models.PositiveIntegerField()
    
    # --- Stunden-Snapshots ---
    total_planned_hours = models.FloatField(default=0.0)    # Summe get_expected_hours_for_date
    total_actual_hours = models.FloatField(default=0.0)     # Summe WorkDay.total_hours
    
    # --- Fehlzeiten-Zähler ---
    vacation_days_taken = models.FloatField(default=0.0)    # Tage mit DayType.VACATION
    sick_days = models.IntegerField(default=0)              # Tage mit DayType.SICK
    holiday_days = models.IntegerField(default=0)           # Tage mit DayType.HOLIDAY
    
    # --- Überstunden-Kette ---
    overtime_at_start = models.FloatField(default=0.0)      # Übertrag aus Vormonat
    overtime_diff = models.FloatField(default=0.0)          # Ist - Soll (dieser Monat)
    overtime_at_end = models.FloatField(default=0.0)        # Neuer Kontostand
    
    is_locked = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"Balance {self.month:02d}/{self.year} - {self.employee.name}"

    def save(self, *args, **kwargs):
        # Automatische Berechnung der Monats-Statistik vor dem Speichern
        self.overtime_diff = self.total_actual_hours - self.total_planned_hours
        self.overtime_at_end = self.overtime_at_start + self.overtime_diff
        super().save(*args, **kwargs)

    def get_previous_balance(self):
        """Sucht die Balance des Vormonats"""
        if self.month == 1:
            p_month, p_year = 12, self.year - 1
        else:
            p_month, p_year = self.month - 1, self.year
        return MonthlyBalance.objects.filter(employee=self.employee, month=p_month, year=p_year).first()

    def sync_with_db(self):
        """
        Synchronisiert den Snapshot mit den echten WorkDays und WorkSessions.
        """
        if self.is_locked:
            return False

        from attendance.models import WorkDay # Lokaler Import gegen Circular Import
        
        # 1. Zeitraum definieren
        first_day = datetime.date(self.year, self.month, 1)
        last_day_num = calendar.monthrange(self.year, self.month)[1]
        
        # 2. Bestehende WorkDays dieses Monats holen
        workdays = WorkDay.objects.filter(
            employee=self.employee, 
            date__year=self.year, 
            date__month=self.month
        )

        # 3. Summen berechnen
        actual_sum = 0.0
        planned_sum = 0.0
        v_days = 0.0
        s_days = 0
        h_days = 0

        # Wir loopen über jeden Tag des Monats, um auch Tage ohne WorkDay-Eintrag (Soll) zu erfassen
        for day in range(1, last_day_num + 1):
            current_date = datetime.date(self.year, self.month, day)
            
            # Soll-Stunden (aus deinem Employee Model)
            planned_sum += self.employee.get_expected_hours_for_date(current_date)
            
            # Ist-Stunden & Typen (aus deinem WorkDay Model)
            wd = workdays.filter(date=current_date).first()
            if wd:
                actual_sum += wd.total_hours # Nutzt deine @property total_hours
                
                if wd.day_type == WorkDay.DayType.VACATION:
                    v_days += 1
                elif wd.day_type == WorkDay.DayType.SICK:
                    s_days += 1
                elif wd.day_type == WorkDay.DayType.HOLIDAY:
                    h_days += 1

        # 4. Daten in Snapshot schreiben
        self.total_planned_hours = round(planned_sum, 2)
        self.total_actual_hours = round(actual_sum, 2)
        self.vacation_days_taken = v_days
        self.sick_days = s_days
        self.holiday_days = h_days

        # 5. Übertrag vom Vormonat laden
        prev = self.get_previous_balance()
        self.overtime_at_start = prev.overtime_at_end if prev else 0.0

        self.save()
        return True



class Notification(models.Model):
    reference_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    recipient = models.ForeignKey(Employee, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, default='info')
    read = models.BooleanField(default=False)
    is_deleted_by_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link_to = models.CharField(max_length=255, blank=True, null=True)


    class Meta:
        ordering = ['-created_at'] # Neueste zuerst

    def __str__(self):
        return f"Notification for {self.recipient.email} - {self.title}"


class Scratchpad(models.Model):
    # OneToOne stellt sicher, dass jeder Mitarbeiter genau eine Notiz hat
    employee = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scratchpad'
    )
    # TextField nimmt das formatierte HTML deines Editors auf
    content = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notizfeld"
        verbose_name_plural = "Notizfelder"

    def __str__(self):
        return f"Notizblock von {self.employee.name}"
    
class TodoItem(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='todos'
    )
    text = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # Älteste zuerst, neue werden unten angehängt

    def __str__(self):
        return f"Todo für {self.employee.username}: {self.text[:20]}"
import datetime
import calendar
from datetime import date
import holidays
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from .utils import user_profile_photo_upload
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.conf import settings
from django.core.exceptions import ValidationError

class Employee(AbstractUser):
    # E-Mail wird optional, da Offline-Betrieb
    email = models.EmailField(blank=True, null=True, unique=False)
    chip_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    phone = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to=user_profile_photo_upload, blank=True, null=True)

    
    joined_at = models.DateField(default=timezone.now)
    vacation_days_per_year = models.DecimalField(max_digits=5, decimal_places=2, default=30.0)

    def get_schema_for_date(self, date_obj):
        """Holt das für dieses Datum gültige Arbeitszeitschema."""
        history = self.time_histories.filter(valid_from__lte=date_obj).order_by('-valid_from').first()
        if history:
            return history.work_days_schema
        
        # Fallback, falls kein Eintrag existiert (z.B. Migration aus Altdaten)
        return getattr(self, '_legacy_work_days_schema', {})

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
    

    def get_schema_for_date(self, date_obj):
        """Holt das für dieses Datum gültige Arbeitszeitschema."""
        history = self.time_histories.filter(valid_from__lte=date_obj).order_by('-valid_from').first()
        if history:
            return history.work_days_schema
        return getattr(self, '_legacy_work_days_schema', {})

    @property
    def work_days_schema(self):
        """
        Rückwärtskompatibel: aktuell (heute) gültiges Schema.
        Für ein bestimmtes Datum bitte get_schema_for_date(date_obj) nutzen!
        """
        return self.get_schema_for_date(timezone.localdate())

    @staticmethod
    def normalize_schema(schema):
        """
        Normalisiert ein Schema für Vergleiche: Keys als Strings, Werte als float.
        Verhindert False-Positives durch z.B. 8 vs. 8.0 oder Key-Reihenfolge.
        """
        return {str(k): float(v) for k, v in (schema or {}).items()}

    @property
    def hours_per_day(self) -> float:
        """
        Berechnet die durchschnittliche tägliche Arbeitszeit basierend auf den 
        Tagen, an denen der Mitarbeiter laut Schema tatsächlich arbeitet.
        Beispiel: 38 Std verteilt auf 5 Tage = 7.6 Std/Tag.
        """
        total_hours = self.weekly_hours  # Nutzt dein bestehendes Property
        
        # Zählen, an wie vielen Tagen laut Schema gearbeitet wird
        active_days_count = 0
        for i in range(7):
            weekday_key = str(i)
            if weekday_key in self.work_days_schema:
                if float(self.work_days_schema[weekday_key]) > 0:
                    active_days_count += 1
            elif i < 5:
                # Fallback für Werktage
                active_days_count += 1
                
        if active_days_count == 0:
            return float(getattr(self, 'hours_per_day', 8.0))
            
        return round(total_hours / active_days_count, 2)

    def get_expected_hours_for_date(self, date_obj):
        from attendance.models import WorkDay
        db_day = WorkDay.objects.filter(employee=self, date=date_obj).first()
        if db_day and db_day.day_type in [WorkDay.DayType.VACATION, WorkDay.DayType.SICK]:
            return 0.0

        if self.is_holiday(date_obj) or self.is_absent(date_obj):
            return 0.0

        schema = self.get_schema_for_date(date_obj)
        weekday_key = str(date_obj.weekday())
        if weekday_key in schema:
            return float(schema[weekday_key])

        if date_obj.weekday() < 5:
            return float(self.hours_per_day)

        return 0.0

    def get_expected_hours_for_month(self, year: int, month: int) -> float:
        _, num_days = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        from attendance.models import WorkDay, LeaveRequest

        db_days = {
            wd.date: wd.day_type
            for wd in WorkDay.objects.filter(employee=self, date__range=(start_date, end_date))
        }

        approved_leaves = LeaveRequest.objects.filter(
            employee=self, status='approved',
            leave_start__lte=end_date, leave_end__gte=start_date
        )
        absent_dates = set()
        for leave in approved_leaves:
            curr = max(leave.leave_start, start_date)
            last = min(leave.leave_end, end_date)
            while curr <= last:
                absent_dates.add(curr)
                curr += datetime.timedelta(days=1)

        de_holidays = holidays.Germany(subdiv='BW', years=year)

        # NEU: alle relevanten Schema-Wechsel einmalig laden, aufsteigend sortiert
        schema_history = list(
            self.time_histories.filter(valid_from__lte=end_date)
            .order_by('valid_from')
            .values_list('valid_from', 'work_days_schema')
        )

        def schema_for(d):
            applicable = None
            for valid_from, schema in schema_history:
                if valid_from <= d:
                    applicable = schema
                else:
                    break
            return applicable or {}

        total_expected = 0.0
        for day in range(1, num_days + 1):
            date_obj = date(year, month, day)
            if date_obj < self.joined_at:
                continue
            if db_days.get(date_obj) in [WorkDay.DayType.VACATION, WorkDay.DayType.SICK]:
                continue
            if date_obj in de_holidays or date_obj in absent_dates:
                continue

            schema = schema_for(date_obj)
            weekday_key = str(date_obj.weekday())
            if weekday_key in schema:
                total_expected += float(schema[weekday_key])
            elif date_obj.weekday() < 5:
                total_expected += float(self.hours_per_day)

        return round(total_expected, 2)

    def save(self, *args, **kwargs):

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

    def get_hours_balance_for_month(self, year: int, month: int) -> dict:
        """
        Berechnet die Ist-Stunden, Soll-Stunden und die daraus resultierende
        Differenz für einen spezifischen Monat.
        """
        from attendance.models import WorkDay
        import calendar

        if self.is_superuser:
            return {"worked": 0.0, "expected": 0.0, "balance": 0.0}

        # Alle WorkDays dieses Monats holen
        workdays = WorkDay.objects.filter(
            employee=self,
            date__year=year,
            date__month=month
        )

        # 1. Ist-Stunden summen
        total_worked = sum(day.total_hours for day in workdays)

        # 2. Soll-Stunden berechnen (nutzt deine bestehende Methode)
        total_expected = self.get_expected_hours_for_month(year, month)

        # 3. Differenz ermitteln
        balance = total_worked - total_expected

        return {
            "worked": round(total_worked, 2),
            "expected": round(total_expected, 2),
            "balance": round(balance, 2)
        }


class WorkingTimeHistory(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="time_histories")
    valid_from = models.DateField(default=timezone.now)
    work_days_schema = models.JSONField(
        default=dict,
        help_text="Format: {'0': 8, '1': 8...} (0=Mo, 6=So)."
    )

    class Meta:
        ordering = ['-valid_from']
        verbose_name = "Arbeitszeit-Historie"
        verbose_name_plural = "Arbeitszeit-Historien"
        constraints = [
            models.UniqueConstraint(fields=['employee', 'valid_from'], name='unique_schema_per_employee_and_date')
        ]

    def __str__(self):
        return f"{self.employee.name} ab {self.valid_from}"


class VacationQuota(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='vacation_quotas')
    year = models.PositiveIntegerField()
    total_days = models.DecimalField(max_digits=5, decimal_places=2)
    carried_over = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    class Meta:
        unique_together = ('employee', 'year')


class MonthlyPayout(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="payouts"
    )
    year = models.IntegerField()
    month = models.IntegerField()
    
    worked_hours = models.DecimalField(max_digits=6, decimal_places=2)
    expected_hours = models.DecimalField(max_digits=6, decimal_places=2)
    
    # Die tatsächlich ermittelten Überstunden
    overtime_calculated = models.DecimalField(max_digits=5, decimal_places=2)
    # Falls der Chef manuell die Auszahlung anpasst (z.B. Rundung oder Kappung)
    overtime_paid = models.DecimalField(max_digits=5, decimal_places=2)
    
    is_processed = models.BooleanField(default=False, help_text="Vom Chef/HR freigegeben")
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('employee', 'year', 'month')
        verbose_name = "Monatsabrechnung"
        verbose_name_plural = "Monatsabrechnungen"

    # In MonthlyPayout:
    def clean(self):
        super().clean()
        
        # Zukunftsschutz bleibt wichtig
        current_date = timezone.now().date()
        if self.year > current_date.year or (self.year == current_date.year and self.month > current_date.month):
            raise ValidationError("Es können keine Abrechnungen für zukünftige Monate erstellt werden.")

        if self.pk:
            original = MonthlyPayout.objects.get(pk=self.pk)
            
            # Wenn die Abrechnung bereits verarbeitet/ausgezahlt wurde
            if original.is_processed:
                # Wenn ein Admin sie wieder öffnen möchte (is_processed von True auf False)
                if not self.is_processed:
                    # Das ist erlaubt, wir setzen processed_at zurück
                    self.processed_at = None
                    return

                # Wenn sie geschlossen bleibt, schützen wir die Systemwerte vor versehentlicher Änderung im Admin
                if (self.worked_hours != original.worked_hours or 
                    self.expected_hours != original.expected_hours or 
                    self.overtime_calculated != original.overtime_calculated):
                    raise ValidationError(
                        "Die berechneten System-Basisstunden einer abgeschlossenen Abrechnung "
                        "können nicht geändert werden. Öffne die Abrechnung zuerst wieder."
                    )

    def save(self, *args, **kwargs):
        if self.is_processed and not self.processed_at:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.name} - {self.month:02d}/{self.year}: {self.overtime_paid} Std ausgezahlt"


class Notification(models.Model):
    # Deine bestehenden Felder...
    recipient = models.ForeignKey('core.Employee', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, default='info')
    link_to = models.CharField(max_length=100, null=True, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # --- Die neuen Felder für Generic Foreign Keys ---
    # 1. Zeigt auf die Tabelle (z.B. "WSChangeRequest" oder "Leave")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    # 2. Speichert die ID des konkreten Antrags (z.B. 12)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    # 3. Das "virtuelle" Feld, das beides verbindet
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        # Ein Index beschleunigt das Suchen nach verknüpften Objekten enorm
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]


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
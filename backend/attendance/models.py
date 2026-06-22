from django.db import models, transaction
from core.models import Employee
from django.utils.timezone import now
from django.utils.timezone import localtime
from django.core.exceptions import ValidationError
from django.db.models import Sum, F, Q, ExpressionWrapper, DurationField
from datetime import timedelta, date, datetime
import holidays



class WorkDay(models.Model):
    class Meta:
        verbose_name = "Work Day"
        verbose_name_plural = "Work Days"
        unique_together = ('employee', 'date')
    
    employee = models.ForeignKey("core.Employee", related_name="workdays", on_delete=models.CASCADE)
    date = models.DateField()
    note = models.TextField(blank=True)

    class DayType(models.TextChoices):
        WORK = "work", "Arbeitstag"
        VACATION = "vacation", "Urlaub"
        OVERTIME = "overtime", "GLZ-Abbau"
        SICK = "sick", "Krank"
        WEEKEND = "weekend", "Wochenende"
        HOLIDAY = "holiday", "Feiertag"

    day_type = models.CharField(
        max_length=10,
        choices=DayType.choices,
        default=DayType.WORK
    )

    def save(self, *args, **kwargs):
        if self.day_type == self.DayType.WORK: 
            calculated_type = self.determine_type()
            if calculated_type:
                self.day_type = calculated_type
                
        super().save(*args, **kwargs)

    def determine_type(self):
        from .models import LeaveRequest
        
        leave = LeaveRequest.objects.filter(
            employee=self.employee,
            leave_start__lte=self.date,
            leave_end__gte=self.date,
            status='approved'
        ).first()
        
        if leave:
            # Mapping von LeaveRequest Typen zu WorkDay DayTypes
            mapping = {
                'vacation': self.DayType.VACATION,
                'sick': self.DayType.SICK,
                'overtime': self.DayType.OVERTIME
            }
            return mapping.get(leave.leave_type, self.DayType.WORK)

        # 2. Check auf Feiertage
        de_holidays = holidays.Germany(
            prov='BW', 
            language='de'
        )

        if self.date in de_holidays:
            return self.DayType.HOLIDAY

        # 3. Check auf Wochenende
        if self.date.weekday() >= 5:
            return self.DayType.WEEKEND

        # 4. Standard
        return self.DayType.WORK



    @property
    def total_hours(self):
        """
        Berechnet die reine Summe der geleisteten Arbeitsstunden (Ist-Stunden) für diesen Tag.
        Berücksichtigt nur abgeschlossene Sessions (mit check_out).
        """
        from datetime import timedelta
        from django.db.models import Sum, F, ExpressionWrapper, DurationField

        # Berechnung der Dauer aller Sessions dieses Tages
        duration = self.sessions.filter(check_out__isnull=False).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("check_out") - F("check_in"), 
                    output_field=DurationField()
                )
            )
        )["total"] or timedelta()

        # Umwandlung von timedelta in Stunden (float)
        return round(duration.total_seconds() / 3600, 2)
    

    def __str__(self):
        return f"{self.date} | {self.employee} ({self.day_type})"


    
class WorkSession(models.Model):
    class Meta:
        verbose_name = "Work Session"
        verbose_name_plural = "Work Sessions"

    work_day = models.ForeignKey(WorkDay, related_name='sessions', on_delete=models.CASCADE)  # Link to WorkDay
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    old_ver_exists = models.BooleanField(default=False)


    def employee(self):
        return self.work_day.employee

    @property
    def status(self):
        return "Eingestempelt" if self.check_out is None else "Ausgestempelt"

    @property
    def is_editable(self):
        if not self.check_out or self.old_ver_exists:
            return False
        # Erlaubt Bearbeitung für 12 Stunden nach Check-out
        return now() <= self.check_out + timedelta(hours=12)

    @property
    def get_date(self):
        return self.check_in.strftime('%d.%m.%Y')
    
    @property
    def duration_str(self):
        if self.check_out is None:
            return "-"
        
        seconds = int((self.check_out - self.check_in).total_seconds())
        return "{:02d}:{:02d}".format(*divmod(seconds // 60, 60))
    

    def most_recent(self):
        return self.check_out or self.check_in

    def end_session(self):

        with transaction.atomic():
            self.check_out = now()
            self.full_clean()
            self.save()
    

    def __str__(self):
        return f"{self.work_day.employee} - {self.check_in} to {self.check_out or 'Still working'}"
    
    def clean(self):
        super().clean()

        # Ensure check_in is before check_out
        if self.check_out and self.check_in >= self.check_out:
            raise ValidationError("Check-in time must be before check-out time.")

        # Check for overlapping sessions
        if self.check_out:
            overlapping_sessions = WorkSession.objects.filter(
                work_day=self.work_day,
                check_out__gt=self.check_in,
                check_in__lt=self.check_out
            )

            if self.pk:
                overlapping_sessions = overlapping_sessions.exclude(pk=self.pk)

            if overlapping_sessions.exists():
                raise ValidationError("This work session overlaps with an existing session.")

class WorkSessionHistory(models.Model):
    class Meta:
        verbose_name = "Old Worksession"
        verbose_name_plural = "Old Worksessions"

    worksession = models.ForeignKey(WorkSession, on_delete=models.CASCADE)
    original_checkin = models.DateTimeField()
    original_checkout = models.DateTimeField()



class WSChangeRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'In Bearbeitung'),
        ('approved', 'Genehmigt'),
        ('rejected', 'Abgelehnt'),
        ('cancelled', 'Storniert')
    ]

    # --- Verknüpfungen ---
    # Optional für Neuanlagen (null=True)
    worksession = models.ForeignKey(
        'WorkSession', 
        on_delete=models.CASCADE, 
        related_name="change_requests", 
        null=True, 
        blank=True
    )
    
    # Der Anker für den Tag (notwendig für Neuanlagen)
    work_day = models.ForeignKey(
        'WorkDay', 
        on_delete=models.CASCADE, 
        related_name="change_requests"
    )

    # --- Daten-Snapshot (für den Vergleich im Admin-Panel) ---
    old_check_in = models.DateTimeField(null=True, blank=True, help_text="Originalzeit beim Erstellen")
    old_check_out = models.DateTimeField(null=True, blank=True)
    
    # --- Beantragte Zeiten ---
    requested_check_in = models.DateTimeField()
    requested_check_out = models.DateTimeField()

    # --- Notizen & Status ---
    employee_note = models.TextField(blank=True, verbose_name="Begründung Mitarbeiter")
    admin_note = models.TextField(blank=True, verbose_name="Kommentar Vorgesetzter")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # --- Meta-Daten ---
    requested_by = models.ForeignKey('core.Employee', on_delete=models.CASCADE, related_name="change_requests")
    reviewed_by = models.ForeignKey('core.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_changes")
    request_date = models.DateTimeField(auto_now_add=True)
    reviewed_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Change Request"
        verbose_name_plural = "Change Requests"
        constraints = [
            # Verhindert doppelte offene Korrekturanträge für dieselbe Session
            models.UniqueConstraint(
                fields=["worksession"],
                condition=models.Q(status="pending", worksession__isnull=False),
                name="unique_pending_session_request"
            ),
            # Verhindert doppelte offene Neuanlagen für denselben Tag
            models.UniqueConstraint(
                fields=["work_day"],
                condition=models.Q(status="pending", worksession__isnull=True),
                name="unique_pending_manual_request"
            )
        ]

    def clean(self):
        """Logische Validierung der Zeiten"""
        if self.requested_check_in and self.requested_check_out:
            if self.requested_check_out <= self.requested_check_in:
                raise ValidationError("Das Ende muss nach dem Beginn liegen.")

    def save(self, *args, **kwargs):
        """Automatische Felder beim ersten Speichern befüllen"""
        if not self.pk:
            if self.worksession:
                # Korrektur: Werte von der Session spiegeln
                self.old_check_in = self.worksession.check_in
                self.old_check_out = self.worksession.check_out
                self.work_day = self.worksession.work_day
                self.requested_by = self.worksession.work_day.employee
            else:
                # Neuanlage: Keine alten Zeiten vorhanden
                self.old_check_in = None
                self.old_check_out = None
                # requested_by muss hier manuell oder via View gesetzt werden
        super().save(*args, **kwargs)

    def approve(self, reviewer):
        """Genehmigt den Antrag und erstellt/aktualisiert die WorkSession"""
        with transaction.atomic():
            # 1. Überlappungsprüfung
            overlapping = self.work_day.sessions.filter(
                check_in__lt=self.requested_check_out,
                check_out__gt=self.requested_check_in
            )
            if self.worksession:
                overlapping = overlapping.exclude(id=self.worksession.id)

            if overlapping.exists():
                raise ValidationError("Überschneidung mit existierenden Arbeitszeiten.")

            # 2. WorkSession behandeln
            from .models import WorkSession, WorkSessionHistory
            
            if self.worksession:
                # Historie für bestehende Session anlegen
                WorkSessionHistory.objects.create(
                    worksession=self.worksession,
                    original_checkin=self.old_check_in,
                    original_checkout=self.old_check_out or self.old_check_in
                )
                session = self.worksession
            else:
                # Neue Session für den Tag erstellen
                session = WorkSession(work_day=self.work_day)

            # 3. Session-Werte setzen
            session.check_in = self.requested_check_in
            session.check_out = self.requested_check_out
            session.old_ver_exists = True # Markiert als manuell bearbeitet/korrigiert
            session.full_clean()
            session.save()

            # 4. Antrag finalisieren
            self.status = 'approved'
            self.reviewed_by = reviewer
            self.reviewed_date = now()
            self.save()

    def reject(self, reviewer, reason):
        """Lehnt den Antrag ab"""
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.admin_note = reason
        self.reviewed_date = now()
        self.save()

    @property
    def is_new_entry(self):
        """Hilfs-Property für das Frontend/Admin"""
        return self.worksession is None


    def requester(self):
        """Gibt den Mitarbeiter zurück, dem dieser Tag gehört"""
        return self.work_day.employee

    @property
    def duration_difference(self):
        """Berechnet die Differenz zwischen alter und neuer Dauer in Sekunden"""
        # Neue Dauer berechnen
        new_dur = (self.requested_check_out - self.requested_check_in).total_seconds()
        
        # Alte Dauer berechnen (0, falls es eine Neuanlage ohne old_check_in ist)
        if self.old_check_in and self.old_check_out:
            old_dur = (self.old_check_out - self.old_check_in).total_seconds()
        else:
            old_dur = 0
            
        return new_dur - old_dur
    

class LeaveRequest(models.Model):

    class Meta:
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"
        ordering = ["-leave_start"]

    STATUS_CHOICES = [
        ("pending", "In Bearbeitung"),
        ("approved", "Genehmigt"),
        ("rejected", "Abgelehnt"),
        ("cancelled", "Storniert")
    ]

    LEAVE_CHOICES = [
        ("sick", "Krank"),
        ("vacation", "Urlaub"),
        ("overtime", "GLZ-Abbau"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_requests"
    )

    leave_type = models.CharField(
        max_length=20,
        choices=LEAVE_CHOICES,
        default="vacation"
    )

    leave_start = models.DateField()
    leave_end = models.DateField()

    reviewed_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_leaves"
    )

    request_date = models.DateTimeField(auto_now_add=True)
    reviewed_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    note = models.TextField(blank=True)

    # -------------------------
    # Validation
    # -------------------------
    def clean(self):
        super().clean()
        if not self.employee_id:
            return

        if self.leave_start > self.leave_end:
            raise ValidationError("Das Startdatum muss vor oder am Enddatum liegen.")

        # Überlappungsprüfung
        overlaps = LeaveRequest.objects.filter(
            employee=self.employee,
            status__in=["pending", "approved"],
            leave_start__lte=self.leave_end,
            leave_end__gte=self.leave_start,
        ).exclude(pk=self.pk)

        if overlaps.exists():
            raise ValidationError("Dieser Zeitraum überschneidet sich mit einem bestehenden Antrag.")


        if self.actual_vacation_days_to_deduct() == 0 and self.leave_type == 'vacation':
            raise ValidationError("Dieser Zeitraum enthält keine Werktage, die vom Urlaubskonto abgezogen werden könnten.")

    # -------------------------
    # Helper
    # -------------------------

    def get_affected_dates(self):
        """
        Returns a list of all weekdays (Mon-Fri) covered by this leave.
        """
        days = []
        current = self.leave_start
        while current <= self.leave_end:
            # Check if the current day is a weekday (Mon-Fri)
            if current.weekday() < 5:
                days.append(current)
            current += timedelta(days=1)
        return days
    
    def num_vacdays(self):
        return len(self.get_affected_dates())

    def approve(self, user):
        """Genehmigt den Antrag und schreibt die WorkDay-Tabelle fort."""

        from . import WorkDay

        with transaction.atomic():
            self.status = "approved"
            self.reviewed_by = user
            self.reviewed_date = now()
            self.save()
            
            # Kalender synchronisieren
            # Wir nutzen das Bundesland des Mitarbeiters (hier Hardcoded 'BW', sollte dynamisch sein)
            de_holidays = holidays.Germany(prov='BW')
            
            current = self.leave_start
            while current <= self.leave_end:
                wd, created = WorkDay.objects.get_or_create(
                    employee=self.employee, 
                    date=current
                )
                
                # REGEWERK FÜR DEN DAY_TYPE:
                # 1. Feiertage behalten ihren Status (Urlaub ist dort 'geschenkt')
                # 2. Wochenenden bleiben Wochenenden
                # 3. Nur Arbeitstage werden zu Urlaub/Krank/GLZ
                is_holiday = current in de_holidays
                is_weekend = current.weekday() >= 5

                if not is_holiday and not is_weekend:
                    wd.day_type = self.map_leave_to_daytype()
                elif is_holiday:
                    wd.day_type = "holiday"
                elif is_weekend:
                    wd.day_type = "weekend"
                
                wd.save()
                current += timedelta(days=1)

    def actual_vacation_days_to_deduct(self):
        """
        Zählt die Netto-Urlaubstage.
        Berücksichtigt Wochenenden UND gesetzliche Feiertage.
        """
        # Tipp: Pro-Mitarbeiter Bundesland nutzen: getattr(self.employee, 'province', 'BW')
        de_holidays = holidays.Germany(prov='BW')
        days = 0
        current = self.leave_start
        while current <= self.leave_end:
            if current.weekday() < 5 and current not in de_holidays:
                days += 1
            current += timedelta(days=1)
        return days

    @property
    def total_days(self):
        """Gibt die Brutto-Dauer in Tagen zurück (für die Anzeige im UI)."""
        return (self.leave_end - self.leave_start).days + 1

    def map_leave_to_daytype(self):
        mapping = {
            "vacation": "vacation",
            "sick": "sick",
            "overtime": "overtime"
        }
        return mapping.get(self.leave_type, "work")

    def __str__(self):
        return f"{self.employee} | {self.leave_type} | {self.leave_start} → {self.leave_end}"


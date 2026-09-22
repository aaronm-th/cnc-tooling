import datetime
from datetime import timedelta
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, F, ExpressionWrapper, DurationField
from django.utils import timezone

from .tasks import generate_workdays_for_range
from core.models import Employee, is_month_locked, first_locked_month
import holidays

from django.utils.timezone import now



class WorkDay(models.Model):
    employee = models.ForeignKey("core.Employee", related_name="workdays", on_delete=models.CASCADE)
    date = models.DateField()
    note = models.TextField(blank=True)

    class DayType(models.TextChoices):
        WORK = "work", "Arbeitstag"
        VACATION = "vacation", "Urlaub"
        SICK = "sick", "Krank"
        WEEKEND = "weekend", "Wochenende"
        HOLIDAY = "holiday", "Feiertag"

    day_type = models.CharField(max_length=10, choices=DayType.choices, default=DayType.WORK)

    class Meta:
        verbose_name = "Work Day"
        verbose_name_plural = "Work Days"
        unique_together = ('employee', 'date')

    @property
    def total_hours(self):
        duration = self.sessions.filter(check_out__isnull=False).aggregate(
            total=Sum(ExpressionWrapper(F("check_out") - F("check_in"), output_field=DurationField()))
        )["total"] or datetime.timedelta()
        return round(duration.total_seconds() / 3600, 2)

    def __str__(self):
        return f"{self.date} | {self.employee} ({self.day_type})"


    def get_scheduled_hours(self):
        """Reine Schema-Stunden für den Wochentag – ohne jegliche Abzüge (Feiertag, Urlaub etc.)."""
        if hasattr(self.employee, 'get_scheduled_hours_for_date'):
            return float(self.employee.get_scheduled_hours_for_date(self.date) or 0.0)
        return 8.0 if self.date.weekday() < 5 else 0.0

    def get_credited_hours(self):
        """
        Angerechnete Ist-Stunden für Soll/Ist-Vergleiche:
        - Urlaub/Krank/Feiertag: volle Schema-Stunden (keine Fehlzeiten-Lücke)
        - sonst: tatsächlich erfasste Zeit (Sessions)
        """
        if self.day_type in (self.DayType.VACATION, self.DayType.SICK, self.DayType.HOLIDAY):
            return self.get_scheduled_hours()
        return float(self.total_hours or 0.0)


class WorkSession(models.Model):
    work_day = models.ForeignKey(WorkDay, related_name='sessions', on_delete=models.CASCADE)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    is_auto_checkout = models.BooleanField(default=False, verbose_name="Automatischer Checkout")

    class Meta:
        verbose_name = "Work Session"
        verbose_name_plural = "Work Sessions"

    def clean(self):
        super().clean()
        if self.check_out and self.check_in >= self.check_out:
            raise ValidationError("Check-out muss vor Check-out liegen.")

        # NEU: Monatssperre – tiefste Sicherheitsnetz-Ebene. Greift für JEDE
        # WorkSession, egal über welchen Codepfad sie erzeugt/geändert wird.
        if is_month_locked(self.work_day.employee, self.work_day.date):
            raise ValidationError(
                "Dieser Monat ist bereits abgeschlossen. Zeiten können nicht mehr geändert werden."
            )

        # Validierung gegen ALLE Sessions des Mitarbeiters (auch tagübergreifend)
        overlapping = WorkSession.objects.filter(
            work_day__employee=self.work_day.employee,
            check_in__lt=self.check_out or timezone.now(),
            check_out__gt=self.check_in
        )
        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)
            
        if overlapping.exists():
            raise ValidationError("Diese Arbeitszeit überschneidet sich mit einer bestehenden Session dieses Mitarbeiters.")

        has_leave = LeaveRequest.objects.filter(
            employee=self.work_day.employee,
            status="approved",
            leave_start__lte=self.work_day.date,
            leave_end__gte=self.work_day.date
        ).exists()

        if has_leave:
            raise ValidationError("An diesem Tag ist bereits ein genehmigter Urlaub/Krankheit hinterlegt. Keine Zeiterfassung möglich.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.work_day.employee} - {self.check_in} to {self.check_out or 'Still working'}"


class WSChangeRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'In Bearbeitung'),
        ('approved', 'Genehmigt'),
        ('rejected', 'Abgelehnt'),
        ('cancelled', 'Storniert')
    ]

    worksession = models.ForeignKey(WorkSession, on_delete=models.CASCADE, related_name="change_requests", null=True, blank=True)
    work_day = models.ForeignKey(WorkDay, on_delete=models.CASCADE, related_name="change_requests")

    old_check_in = models.DateTimeField(null=True, blank=True)
    old_check_out = models.DateTimeField(null=True, blank=True)
    
    requested_check_in = models.DateTimeField()
    requested_check_out = models.DateTimeField()

    employee_note = models.TextField(blank=True, verbose_name="Begründung Mitarbeiter")
    admin_note = models.TextField(blank=True, verbose_name="Kommentar")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    requested_by = models.ForeignKey('core.Employee', on_delete=models.CASCADE, related_name="change_requests")
    reviewed_by = models.ForeignKey('core.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_changes")
    request_date = models.DateTimeField(auto_now_add=True)
    reviewed_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Change Request"
        verbose_name_plural = "Change Requests"
        constraints = [
            models.UniqueConstraint(
                fields=["worksession"],
                condition=models.Q(status="pending", worksession__isnull=False),
                name="unique_pending_session_request"
            ),
        ]

    @property
    def duration_difference_minutes(self):
        """
        Berechnet die Differenz der Arbeitszeit in Minuten.
        Positiv = Mehrarbeitszeit, Negativ = Weniger Arbeitszeit.
        """
        if not self.requested_check_in or not self.requested_check_out:
            return 0

        # Dauer des Antrags in Minuten
        requested_duration = (self.requested_check_out - self.requested_check_in).total_seconds() / 60

        # Dauer der alten Session (falls vorhanden)
        old_duration = 0
        if self.old_check_in and self.old_check_out:
            old_duration = (self.old_check_out - self.old_check_in).total_seconds() / 60
            
        elif self.worksession and self.worksession.check_out and self.worksession.check_in:
            old_duration = (self.worksession.check_out - self.worksession.check_in).total_seconds() / 60

        # Differenz berechnen und runden
        return round(requested_duration - old_duration)

    def clean(self):
        super().clean()
        
        # 1. Zeiten-Validierung
        if self.requested_check_in and self.requested_check_out:
            if self.requested_check_out <= self.requested_check_in:
                raise ValidationError("Das Ende muss nach dem Beginn liegen.")

        # Mitarbeiter-Ermittlung für die folgenden Prüfungen
        employee = None
        if self.worksession:
            employee = self.worksession.work_day.employee
        elif hasattr(self, 'requested_by') and self.requested_by:
            employee = self.requested_by
        elif self.work_day:
            employee = self.work_day.employee

        if employee and self.requested_check_in and self.requested_check_out:
            # A. Prüfung gegen Eintrittsdatum (joined_at)
            if hasattr(employee, 'joined_at') and employee.joined_at:
                if self.requested_check_in.date() < employee.joined_at:
                    raise ValidationError(
                        f"Die Arbeitszeit liegt vor dem Eintrittsdatum des Mitarbeiters ({employee.joined_at.strftime('%d.%m.%Y')})."
                    )

            # B. Prüfung gegen genehmigten Urlaub / Krankheit
            requested_date = self.requested_check_in.date()
            has_leave = LeaveRequest.objects.filter(
                employee=employee,
                status="approved",
                leave_start__lte=requested_date,
                leave_end__gte=requested_date
            ).exists()
            if has_leave:
                raise ValidationError(
                    "Für diesen Tag liegt bereits ein genehmigter Urlaubs- oder Krankheitsantrag vor. "
                    "Es können keine Arbeitszeiten korrigiert werden."
                )

            # C. Überlappungsprüfung mit EXISTIERENDEN WorkSessions
            overlapping_sessions = WorkSession.objects.filter(
                work_day__employee=employee,
                check_in__lt=self.requested_check_out,
                check_out__gt=self.requested_check_in
            )
            
            # WICHTIG: Wenn dieser Antrag eine existierende Session KORRIGIEREN soll,
            # müssen wir diese eine Session von der Prüfung ausschließen.
            if self.worksession:
                overlapping_sessions = overlapping_sessions.exclude(pk=self.worksession.pk)
                
            if overlapping_sessions.exists():
                raise ValidationError(
                    "Dieser Zeitraum überschneidet sich mit einer bereits erfassten Arbeitszeit."
                )

            # D. Überlappungsprüfung mit anderen PENDING Change Requests (bestehend)
            overlapping_requests = WSChangeRequest.objects.filter(
                status='pending',
                work_day__employee=employee,
                requested_check_in__lt=self.requested_check_out,
                requested_check_out__gt=self.requested_check_in
            )
            if self.pk:
                overlapping_requests = overlapping_requests.exclude(pk=self.pk)
            if overlapping_requests.exists():
                raise ValidationError(
                    "Es existiert bereits ein ausstehender Korrekturantrag, der sich mit diesem Zeitraum überschneidet."
                )

        # 2. Konsistenz-Validierung (bestehend)
        if self.worksession and self.work_day:
            if self.worksession.work_day != self.work_day:
                raise ValidationError(
                    "Kritischer Fehler: Der ausgewählte Arbeitstag stimmt nicht mit dem Tag der Arbeitszeit überein."
                )

    def save(self, *args, **kwargs):
        self.full_clean()

        if self.worksession:
            # old_check_in/old_check_out nur bei der Erstanlage aus der Session ableiten.
            # Bei approve() wurde die Session zu diesem Zeitpunkt bereits auf die neuen
            # Zeiten aktualisiert – ein erneutes Ableiten würde old_* mit den neuen
            # Werten überschreiben und duration_difference_minutes verfälschen.
            if self.pk is None:
                self.old_check_in = self.worksession.check_in
                self.old_check_out = self.worksession.check_out
            self.work_day = self.worksession.work_day
            self.requested_by = self.worksession.work_day.employee

        super().save(*args, **kwargs)

    def approve(self, reviewer):
        """ Genehmigt den Antrag und aktualisiert/erstellt die WorkSession direkt """
        # NEU: Monatssperre prüfen, BEVOR irgendetwas verändert wird. Fängt den
        # Fall ab, dass ein Antrag vor Monatsabschluss gestellt, aber erst
        # danach genehmigt wird.
        if is_month_locked(self.work_day.employee, self.work_day.date):
            raise ValidationError(
                f"Der Monat {self.work_day.date.strftime('%m/%Y')} ist bereits abgeschlossen und kann nicht mehr bearbeitet werden."
            )

        with transaction.atomic():
            # Überlappungsprüfung
            overlapping = self.work_day.sessions.filter(
                check_in__lt=self.requested_check_out,
                check_out__gt=self.requested_check_in
            )
            if self.worksession:
                overlapping = overlapping.exclude(id=self.worksession.id)

            if overlapping.exists():
                raise ValidationError("Überschneidung mit existierenden Arbeitszeiten.")

            # Existierende Session updaten oder neue erstellen
            if self.worksession:
                session = self.worksession
            else:
                session = WorkSession(work_day=self.work_day)

            # Zeiten direkt überschreiben (In-Place)
            session.check_in = self.requested_check_in
            session.check_out = self.requested_check_out
            session.full_clean()
            session.save()

            # NEU: Verknüpfung setzen – sonst schließt clean() beim folgenden self.save()
            # die soeben erstellte/aktualisierte Session nicht von der Überlappungsprüfung
            # aus und schlägt fälschlich gegen sich selbst fehl.
            self.worksession = session

            # Antrag abschließen
            self.status = 'approved'
            self.reviewed_by = reviewer
            self.reviewed_date = timezone.now()
            self.save()


    def reject(self, reviewer, reason):
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.admin_note = reason
        self.reviewed_date = timezone.now()
        self.save()


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

        # WICHTIG: Wenn der Antrag storniert oder abgelehnt ist/wird, 
        # müssen wir vergangene Daten oder Überlappungen nicht mehr blockieren.
        # (Bewusst KEINE Monatssperr-Prüfung hier: sonst würde auch reject()/
        # cancel() über gesperrte Zeiträume blockiert, obwohl das unkritisch
        # ist. Die Sperre wird gezielt beim Anlegen (Serializer) und bei der
        # Genehmigung (approve() / Supervisor-View) geprüft.)
        if self.status in ['cancelled', 'rejected']:
            return

        # Prüfung gegen das Eintrittsdatum
        if hasattr(self.employee, 'joined_at') and self.employee.joined_at:
            if self.leave_start < self.employee.joined_at:
                raise ValidationError(f"Der Antrag liegt vor dem Eintrittsdatum...")

        # Prüfung auf Vergangenheit (NUR für neuen/bearbeiteten Urlaub)
        if self.leave_type == 'vacation':
            today = timezone.now().date()
            if self.leave_start < today:
                raise ValidationError("Urlaubsanträge können nicht für die Vergangenheit erstellt werden.")

        # Überlappungsprüfung (nur mit anderen AKTIVEN Anträgen)
        overlaps = LeaveRequest.objects.filter(
            employee=self.employee,
            status__in=["pending", "approved"],
            leave_start__lte=self.leave_end,
            leave_end__gte=self.leave_start,
        )

        # Wir ermitteln die ID so sicher wie möglich, falls self.pk im serializer.clean() temporär None ist
        current_id = self.pk or getattr(self, 'id', None)
        
        if current_id:
            overlaps = overlaps.exclude(pk=current_id)
        # ----------------------------

        if overlaps.exists():
            raise ValidationError("Dieser Zeitraum überschneidet sich mit einem bestehenden Antrag.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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
        # NEU: Monatssperre über den gesamten Zeitraum prüfen, BEVOR irgendetwas
        # verändert wird. Relevant für alle Aufrufer dieser Methode (aktuell
        # nicht die Supervisor-View, aber z.B. Admin-Actions/zukünftiger Code).
        locked_month = first_locked_month(self.employee, self.leave_start, self.leave_end)
        if locked_month:
            raise ValidationError(
                f"Der Monat {locked_month.strftime('%m/%Y')} ist bereits abgeschlossen und kann nicht mehr bearbeitet werden."
            )

        with transaction.atomic():
            self.status = "approved"
            self.reviewed_by = user
            self.reviewed_date = now()
            self.save()
            
            # Wir übergeben den Job an Celery. Der Worker erledigt das im Hintergrund.
            # Keine Blockade im Admin-Bereich, keine komischen Schleifen-Fehler mehr!
            transaction.on_commit(lambda: generate_workdays_for_range.delay(
                self.employee.id, 
                self.leave_start.isoformat(), 
                self.leave_end.isoformat()
            ))

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
        }
        return mapping.get(self.leave_type, "work")

    def __str__(self):
        return f"{self.employee} | {self.leave_type} | {self.leave_start} → {self.leave_end}"

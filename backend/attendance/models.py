import datetime
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, F, ExpressionWrapper, DurationField
from django.utils import timezone

class WorkDay(models.Model):
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


class WorkSession(models.Model):
    work_day = models.ForeignKey(WorkDay, related_name='sessions', on_delete=models.CASCADE)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Work Session"
        verbose_name_plural = "Work Sessions"

    def clean(self):
        super().clean()
        if self.check_out and self.check_in >= self.check_out:
            raise ValidationError("Check-in muss vor Check-out liegen.")

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
            models.UniqueConstraint(
                fields=["work_day"],
                condition=models.Q(status="pending", worksession__isnull=True),
                name="unique_pending_manual_request"
            )
        ]

    def clean(self):
        if self.requested_check_in and self.requested_check_out:
            if self.requested_check_out <= self.requested_check_in:
                raise ValidationError("Das Ende muss nach dem Beginn liegen.")

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.worksession:
                self.old_check_in = self.worksession.check_in
                self.old_check_out = self.worksession.check_out
                self.work_day = self.worksession.work_day
                self.requested_by = self.worksession.work_day.employee
        super().save(*args, **kwargs)

    def approve(self, reviewer):
        """ Genehmigt den Antrag und aktualisiert/erstellt die WorkSession direkt """
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

            # Antrag abschließen
            self.status = 'approved'
            self.reviewed_by = reviewer
            self.reviewed_date = timezone.now()
            self.save()

            # Benachrichtigung senden
            from core.models import Notification
            Notification.objects.create(
                recipient=self.requested_by,
                title="Zeitänderung genehmigt",
                message=f"Dein Korrekturantrag für den {self.work_day.date.strftime('%d.%m.%Y')} wurde freigegeben.",
                notification_type="success"
            )

    def reject(self, reviewer, reason):
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.admin_note = reason
        self.reviewed_date = timezone.now()
        self.save()


class LeaveRequest(models.Model):
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

    employee = models.ForeignKey("core.Employee", on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.CharField(max_length=20, choices=LEAVE_CHOICES, default="vacation")
    leave_start = models.DateField()
    leave_end = models.DateField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    note = models.TextField(blank=True)
    request_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"
        ordering = ["-leave_start"]

    def clean(self):
        super().clean()
        if self.leave_start > self.leave_end:
            raise ValidationError("Das Startdatum muss vor oder am Enddatum liegen.")

        overlaps = LeaveRequest.objects.filter(
            employee=self.employee,
            status__in=["pending", "approved"],
            leave_start__lte=self.leave_end,
            leave_end__gte=self.leave_start,
        ).exclude(pk=self.pk)

        if overlaps.exists():
            raise ValidationError("Dieser Zeitraum überschneidet sich mit einem bestehenden Antrag.")
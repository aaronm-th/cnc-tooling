from django.db import models
from attendance.models import Employee, WorkDay

class Payroll(models.Model):
    employee = models.ForeignKey(Employee, related_name="payrolls", on_delete=models.CASCADE)
    
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Arbeitszeitdaten (eingefroren)
    total_hours = models.FloatField(default=0)
    overtime_hours = models.FloatField(default=0)
    vacation_days = models.IntegerField(default=0)
    sick_days = models.IntegerField(default=0)
    
    # Finanzdaten
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    overtime_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonuses = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Payroll"
        verbose_name_plural = "Payrolls"
        unique_together = ("employee", "period_start", "period_end")

    def __str__(self):
        return f"Payroll {self.employee} ({self.period_start} – {self.period_end})"

    def calculate(self, hours_per_day=8, hourly_rate=20, overtime_rate=25):
        """Berechnet Lohn anhand WorkDays im Zeitraum"""
        workdays = WorkDay.objects.filter(
            employee=self.employee,
            date__gte=self.period_start,
            date__lte=self.period_end
        )

        self.total_hours = sum(w.calculate_total_hours() for w in workdays)
        self.overtime_hours = sum(w.calculate_overtime_hours(hours_per_day) for w in workdays)
        self.vacation_days = workdays.filter(is_vacation=True).count()
        self.sick_days = workdays.filter(is_sick=True).count()

        self.base_salary = self.total_hours * hourly_rate
        self.overtime_payment = self.overtime_hours * (overtime_rate - hourly_rate)
        self.total_salary = self.base_salary + self.overtime_payment + self.bonuses - self.deductions
        self.save()

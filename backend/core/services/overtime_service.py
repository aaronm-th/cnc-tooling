import datetime
from django.utils import timezone

class OvertimeService:
    @staticmethod
    def calculate_balance(employee):
        """Berechnet das aktuelle Überstundenkonto unter Berücksichtigung von Snapshots."""
        from attendance.models import WorkDay
        today = timezone.now().date()
        
        # 1. Letzten Snapshot holen
        last_snapshot = employee.monthly_balances.first()
        
        if last_snapshot:
            balance = last_snapshot.balance_at_end
            if last_snapshot.month == 12:
                start_date = datetime.date(last_snapshot.year + 1, 1, 1)
            else:
                start_date = datetime.date(last_snapshot.year, last_snapshot.month + 1, 1)
        else:
            balance = 0.0
            start_date = employee.joined_at if employee.joined_at else datetime.date(today.year, today.month, 1)

        # 2. Differenz berechnen
        days = WorkDay.objects.filter(
            employee=employee, 
            date__gte=start_date, 
            date__lte=today
        )
        
        for day in days:

            expected_hours = employee.get_expected_hours(day.date)

            if day.day_type == 'work':
                balance += (day.total_hours - expected_hours)
            elif day.day_type == 'overtime': # Gleitzeitabbau
                balance -= expected_hours
        
        return round(balance, 2)
import datetime
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone

class VacationService:
    
    @staticmethod
    def get_total_days_for_year(employee, year) -> Decimal:
        """
        Berechnet den vollen Jahresanspruch. 
        Berücksichtigt den unterjährigen Einstieg (Aliquotierung).
        """
        base_days = getattr(employee, 'vacation_days_per_year', Decimal('30.0')) 
        
        if not employee.joined_at or employee.joined_at.year < year:
            return Decimal(str(base_days))
            
        if employee.joined_at.year == year:
            entry_month = employee.joined_at.month
            months_active = 12 - entry_month + 1 
            
            # Anteilige Berechnung: (Basis-Tage / 12) * Aktive Monate
            pro_rata_days = (Decimal(str(base_days)) / Decimal('12')) * Decimal(str(months_active))
            return pro_rata_days.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            
        return Decimal('0.0')

    @staticmethod
    def get_used_days(employee, year) -> int:
        """Zählt einfach alle genommenen Urlaubstage im laufenden Jahr."""
        from attendance.models import WorkDay
        return WorkDay.objects.filter(
            employee=employee,
            date__year=year,
            day_type='vacation'
        ).count()
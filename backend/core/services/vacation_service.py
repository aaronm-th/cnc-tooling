from decimal import Decimal, ROUND_HALF_UP
import datetime
import math


class VacationService:
    
    @staticmethod
    def calculate_initial_quota(employee, year):
        """
        Berechnet den Urlaubsanspruch für ein bestimmtes Jahr.
        Berücksichtigt unterjährigen Eintritt (Aliquotierung).
        """
        base_days = getattr(employee, 'vacation_days_per_year', Decimal('30.0')) 
        
        if not employee.joined_at:
            return base_days
            
        if employee.joined_at.year < year:
            return base_days
            
        if employee.joined_at.year == year:
            entry_month = employee.joined_at.month
            months_active = 12 - entry_month + 1 
            
            # Präzise Decimal-Berechnung statt fehleranfälligem Float-Prozent-Dividieren
            pro_rata_days = (Decimal(str(base_days)) / Decimal('12')) * Decimal(str(months_active))
            
            # Kaufmännische Rundung auf 0 Nachkommastellen (Ganzzahlige Tage)
            return pro_rata_days.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            
        return Decimal('0.0')

    @staticmethod
    def get_used_days(employee, year) -> int:
        """Holt die summierten Urlaubstage aus dem WorkDay Model."""
        from attendance.models import WorkDay
        return WorkDay.objects.filter(
            employee=employee,
            date__year=year,
            date__lte=datetime.date.today(),
            day_type='vacation'
        ).count()
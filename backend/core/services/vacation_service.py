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
        # Basis-Urlaubsanspruch aus dem Mitarbeiter-Profil (z.B. 30)
        # Falls auf dem Model das Feld anders heißt, entsprechend anpassen
        base_days = getattr(employee, 'vacation_days_per_year', 30) 
        
        if not employee.joined_at:
            return base_days
            
        # Wenn der Eintritt in einem vergangenen Jahr war, gibt es vollen Anspruch
        if employee.joined_at.year < year:
            return base_days
            
        # Wenn der Eintritt im laufenden Berechnungsjahr ist -> Aliquotieren
        if employee.joined_at.year == year:
            entry_month = employee.joined_at.month
            # Verbleibende Monate im Jahr inklusive Eintrittsmonat
            months_active = 12 - entry_month + 1 
            
            pro_rata_days = float(base_days / 12 * months_active)
            
            # Kaufmännische Rundung wie im Frontend (Math.round)
            return int(pro_rata_days + 0.5) if pro_rata_days % 1 >= 0.5 else int(pro_rata_days)
            
        # Eintritt liegt in der Zukunft (nächstes Jahr) -> 0 Tage für dieses Jahr
        return 0

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
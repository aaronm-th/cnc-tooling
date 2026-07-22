from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from core.models import Employee
from .utils import _send_supervisor_notification

MAX_SESSION_DURATION = timedelta(hours=15)

# Helper method
def format_timedelta(td):
    """Formatiert ein timedelta-Objekt in eine lesbare deutsche Form."""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        if minutes > 0:
            return f"{hours} Std. {minutes} Min."
        return f"{hours} Std."
    
    return f"{minutes} Min."


@shared_task
def auto_checkout():
    # 'now' bleibt UTC für die DB-Abfrage
    from .models import WorkSession
    now = timezone.now()
    
    # Für das Log machen wir es lokal lesbar:
    local_now = timezone.localtime(now)
    print(f"[DEBUG] Jetzt (Lokal): {local_now} | Jetzt (UTC): {now}")

    # Alle offenen Sessions anzeigen
    all_open = WorkSession.objects.filter(check_out__isnull=True)
    for s in all_open:
        local_check_in = timezone.localtime(s.check_in)
        print(f"Offene Session: {s.work_day.employee} | Check-in (Lokal): {local_check_in}")
    
    # Der Filter nutzt korrekt UTC im Hintergrund
    overdue_sessions = WorkSession.objects.filter(
        check_out__isnull=True,
        check_in__lt=now - MAX_SESSION_DURATION
    )

    count = 0
    for session in overdue_sessions:
        # Setzt den Checkout exakt 2 Minuten nach dem Check-in
        session.check_out = session.check_in + MAX_SESSION_DURATION
        session.save()

        session.refresh_from_db()
        local_check_out = timezone.localtime(session.check_out)
        print(f"DEBUG: Nach Save - Check_out (Lokal) ist: {local_check_out}")

        employee = session.work_day.employee
        print(f"[AUTO CHECKOUT] {employee} ausgestempelt.")
        count += 1

        readable_duration = format_timedelta(MAX_SESSION_DURATION)

        _send_supervisor_notification(
            title="Automatischer Checkout",
            message=f"{employee.get_full_name()} war mehr als {readable_duration} anwesend und wurde automatisch vom System ausgestempelt.",
            link_to=None
        )

    if count > 0:
        print(f"[AUTO CHECKOUT] Insgesamt {count} User automatisch ausgestempelt.")
    else:
        print("[AUTO CHECKOUT] Keine User zum Ausstempeln gefunden.")



@shared_task
def daily_workday_generation():
    """Wird jede Nacht per Celery Beat ausgeführt."""
    from core.models import Employee
    from django.utils import timezone
    
    today_str = timezone.localdate().isoformat()
    active_employees = Employee.objects.filter(is_active=True, is_superuser=False)
    
    for emp in active_employees:
        # Ruft den Range-Task einfach mit Start=Heute und Ende=Heute auf
        generate_workdays_for_range.delay(emp.id, today_str, today_str)


@shared_task
def generate_workdays_for_range(employee_id, start_date_str, end_date_str):
    from django.utils.dateparse import parse_date
    from core.models import Employee
    from .models import WorkDay, LeaveRequest
    import holidays
    
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)
    emp = Employee.objects.get(id=employee_id)
    de_holidays = holidays.Germany(prov='BW')
    
    current = start_date
    while current <= end_date:
        is_holiday = current in de_holidays
        is_weekend = current.weekday() >= 5
        
        # Prüfen, ob für diesen Tag ein Urlaub vorliegt
        leave = LeaveRequest.objects.filter(
            employee=emp, leave_start__lte=current, leave_end__gte=current, status='approved'
        ).first()
        
        day_type = WorkDay.DayType.WORK
        if leave:
            mapping = {'vacation': WorkDay.DayType.VACATION, 'sick': WorkDay.DayType.SICK, 'overtime': WorkDay.DayType.OVERTIME}
            day_type = mapping.get(leave.leave_type, WorkDay.DayType.WORK)
        elif is_holiday:
            day_type = WorkDay.DayType.HOLIDAY
        elif is_weekend:
            day_type = WorkDay.DayType.WEEKEND
            
        # Nutze get_or_create oder update_or_create, um nichts zu überschreiben, was manuell geändert wurde
        WorkDay.objects.get_or_create(
            employee=emp,
            date=current,
            defaults={'day_type': day_type}
        )
        current += timedelta(days=1)

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import WorkSession, WorkDay
from core.models import Employee

MAX_SESSION_DURATION = timedelta(hours=6)

@shared_task
def auto_checkout():
    now = timezone.now()
    # Debug: Was ist 'jetzt' für den Worker?
    print(f"Jetzt ist {now}")
    print(f"Grenzwert (now - 6h) ist {now - MAX_SESSION_DURATION}")

    # Alle offenen Sessions zum Vergleich anzeigen
    all_open = WorkSession.objects.filter(check_out__isnull=True)
    for s in all_open:
        print(f"Offene Session von {s.work_day.employee}: Check-in war {s.check_in}")
    
    # Der eigentliche Filter
    overdue_sessions = WorkSession.objects.filter(
        check_out__isnull=True,
        check_in__lt=now - MAX_SESSION_DURATION
    )

    count = 0
    for session in overdue_sessions:
        session.check_out = session.check_in + MAX_SESSION_DURATION
        session.save()

        session.refresh_from_db()
        print(f"DEBUG: Nach Save - Check_out ist: {session.check_out}")

        employee = session.work_day.employee

        print(f"[AUTO CHECKOUT] {employee} ausgestempelt.")
        count += 1

    if count > 0:
        print(f"[AUTO CHECKOUT] Insgesamt {count} User automatisch ausgestempelt.")
    else:
        print("[AUTO CHECKOUT] Keine User zum Ausstempeln gefunden.")


@shared_task
def new_workday(target_date=None):
    # Wenn kein Datum übergeben wird, nimm heute
    if target_date is None:
        today = timezone.localdate()
    else:
        # Falls ein String übergeben wurde, parsen
        from django.utils.dateparse import parse_date
        today = parse_date(target_date) if isinstance(target_date, str) else target_date

    # 1. Feiertage einmalig für den Tag laden
    # (Hier ggf. Bundesland dynamisch pro Region laden, falls nötig)
    import holidays
    de_holidays = holidays.Germany(prov='BW')
    is_holiday = today in de_holidays
    is_weekend = today.weekday() >= 5

    employees_to_track = Employee.objects.filter(is_active = True)
    
    # Bereits existierende Tage ausschließen
    existing_ids = WorkDay.objects.filter(date=today).values_list('employee_id', flat=True)
    missing_employees = employees_to_track.exclude(id__in=existing_ids)

    new_days = []
    for emp in missing_employees:
        # Hier die Logik aus determine_type vorziehen
        # Erst auf Urlaub prüfen (da Urlaub Vorrang vor Feiertag/Wochenende hat)
        from attendance.models import LeaveRequest
        leave = LeaveRequest.objects.filter(
            employee=emp,
            leave_start__lte=today,
            leave_end__gte=today,
            status='approved'
        ).first()

        day_type = WorkDay.DayType.WORK # Default
        
        if leave:
            mapping = {
                'vacation': WorkDay.DayType.VACATION,
                'sick': WorkDay.DayType.SICK,
                'overtime': WorkDay.DayType.OVERTIME
            }
            day_type = mapping.get(leave.leave_type, WorkDay.DayType.WORK)
        elif is_holiday:
            day_type = WorkDay.DayType.HOLIDAY
        elif is_weekend:
            day_type = WorkDay.DayType.WEEKEND

        new_days.append(
            WorkDay(
                employee=emp, 
                date=today, 
                day_type=day_type
            )
        )
    
    WorkDay.objects.bulk_create(new_days)
    
            

    

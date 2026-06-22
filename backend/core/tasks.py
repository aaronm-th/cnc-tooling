# your_app/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import Employee, MonthlyBalance
from dateutil.relativedelta import relativedelta
from datetime import timedelta

@shared_task
def generate_monthly_balances():
    # Wir berechnen das Datum des letzten Monats
    last_month_date = timezone.now() - relativedelta(months=1)
    month = last_month_date.month
    year = last_month_date.year

    employees = Employee.objects.filter(is_active=True)
    balances_to_create = []

    for employee in employees:
        # Hier die Logik einfügen, wie die Überstunden berechnet werden
        # Angenommen, das Employee-Modell hat ein Feld 'current_overtime'
        balances_to_create.append(
            MonthlyBalance(
                employee=employee,
                month=month,
                year=year,
                overtime_at_end=employee.current_overtime 
            )
        )

    # Bulk Create für bessere Performance
    MonthlyBalance.objects.bulk_create(
        balances_to_create, 
        ignore_conflicts=True # Verhindert Fehler, falls der Task doppelt läuft
    )
    
    return f"Balances for {month}/{year} created for {len(balances_to_create)} employees."


@shared_task
def sync_all_monthly_balances(month=None, year=None):
    """
    Synchronisiert die MonthlyBalance-Snapshots mit den echten WorkDay-Daten.
    Standardmäßig wird der aktuelle Monat verwendet.
    """
    now = timezone.now()
    target_month = month or now.month
    target_year = year or now.year

    employees = Employee.objects.filter(is_active=True)
    results = {
        "updated": 0,
        "created": 0,
        "locked_skipped": 0
    }

    for employee in employees:
        # 1. MonthlyBalance Objekt holen oder erstellen
        balance, created = MonthlyBalance.objects.get_or_create(
            employee=employee,
            month=target_month,
            year=target_year
        )
        
        if created:
            results["created"] += 1
        
        # 2. Die Logik aus deinem Model aufrufen
        # sync_with_db() berechnet Soll, Ist, Fehlzeiten und Übertrag
        success = balance.sync_with_db()
        
        if success:
            results["updated"] += 1
        else:
            # Falls is_locked = True, gibt sync_with_db False zurück
            results["locked_skipped"] += 1

    return (f"Sync for {target_month}/{target_year} complete: "
            f"{results['updated']} updated, {results['created']} new, "
            f"{results['locked_skipped']} skipped (locked).")



@shared_task
def cleanup_old_notifications():
    from .models import Notification
    from django.utils import timezone
    limit = timezone.now() - timedelta(days=30)
    Notification.objects.filter(created_at__lt=limit, read=True).delete()
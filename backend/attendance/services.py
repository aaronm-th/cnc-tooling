from .models import WorkDay
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils.timezone import localdate


def create_vacation_workdays(leave_request):
    current_date = leave_request.start_date

    while current_date <= leave_request.end_date:
        WorkDay.objects.get_or_create(
            employee=leave_request.employee,
            date=current_date,
            defaults={
                "day_type": WorkDay.DayType.VACATION
            }
        )
        current_date += timedelta(days=1)


def get_or_create_today_workday(employee):
    work_day, created = WorkDay.objects.get_or_create(
        employee=employee,
        date=localdate()
    )

    if work_day.day_type != WorkDay.DayType.WORK:
        raise ValidationError(
            "Check-in is not allowed on vacation or sick days."
        )

    return work_day
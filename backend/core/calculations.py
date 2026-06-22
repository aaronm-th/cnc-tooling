from datetime import time
from django.utils import timezone

def time2decimal(delta_t):
    total_seconds = delta_t.total_seconds()
    decimal_hours = total_seconds / 3600  # Convert seconds to hours
    return round(decimal_hours, 2)  # Optionally round to 2 decimal places

def decimal2time(decimal_hours):
    hours = int(decimal_hours)  # Get the whole number part (hours)
    minutes = int((decimal_hours - hours) * 60)  # Convert fractional part to minutes
    return time(hour=hours, minute=minutes)

def duration2decimal(time1, time2):
    duration = time2-time1
    total_seconds = duration.total_seconds()
    decimal_hours = total_seconds / 3600  # Convert seconds to hours
    return round(decimal_hours, 2)  # Optionally round to 2 decimal places


def utc2local(t):
    return timezone.localtime(t)
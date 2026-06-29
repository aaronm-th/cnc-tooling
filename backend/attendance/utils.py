from core.utils import create_notifications_for_multiple_users
from core.models import Employee

def _send_supervisor_notification(title, message, link_to, **kwargs):
    """
    Interne Hilfsfunktion, die die Logik für Supervisor-Benachrichtigungen bündelt.
    """
    supervisors = Employee.objects.filter(is_superuser=True)
    
    return create_notifications_for_multiple_users(
        recipients=supervisors,
        title=title,
        message=message,
        notification_type='info',
        link_to=link_to,
        **kwargs  # Reicht zusätzliche Argumente wie reference_id flexibel weiter
    )


def send_leave_notification(leave):
    employee = leave.employee
    type_name = leave.get_leave_type_display()
    
    if leave.leave_start == leave.leave_end:
        dates = f"am {leave.leave_start.strftime('%d.%m.%Y')}"
    else:
        dates = f"vom {leave.leave_start.strftime('%d.%m.%Y')} bis {leave.leave_end.strftime('%d.%m.%Y')}"

    _send_supervisor_notification(
        title=f"Neuer Abwesenheitsantrag von {employee.get_full_name()}",
        message=f"{employee.get_full_name()} hat {type_name} {dates} beantragt.",
        link_to='admin-requests',
        content_object=leave 
    )


def send_change_notification(change_request):
    employee = change_request.work_day.employee
    date_str = change_request.work_day.date.strftime('%d.%m.%Y')
   
    _send_supervisor_notification(
        title=f"Neuer Änderungsantrag von {employee.get_full_name()}",
        message=f"{employee.get_full_name()} hat eine Arbeitszeitänderung für den {date_str} beantragt.",
        link_to='admin-requests',
        content_object=change_request
    )
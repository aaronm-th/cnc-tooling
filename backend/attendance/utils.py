def send_leave_notification(leave):
    from core.utils import create_notification
    employee = leave.employee
    if not employee.supervisor:
        return

    type_name = leave.get_leave_type_display()
    dates = f"am {leave.leave_start.strftime('%d.%m.%Y')}" if leave.leave_start == leave.leave_end \
            else f"vom {leave.leave_start.strftime('%d.%m.%Y')} bis {leave.leave_end.strftime('%d.%m.%Y')}"

    create_notification(
        user=employee.supervisor,
        title=f"Neuer Abwesenheitsantrag von {employee.get_full_name()}",
        message=f"{employee.get_full_name()} hat {type_name} {dates} beantragt.",
        notification_type='info',
        link_to='admin-requests'
    )



def send_change_notification(change_request):
    from core.utils import create_notification
    
    # Sicherer Zugriff über die WorkSession, falls requested_by noch nicht in DB steht
    employee = change_request.work_day.employee
    
    # Falls der Mitarbeiter keinen Vorgesetzten hat, können wir niemanden benachrichtigen
    supervisor = getattr(employee, 'supervisor', None)
    if not supervisor:
        return

    # Datum formatieren
    date_str = change_request.work_day.date.strftime('%d.%m.%Y')
   
    create_notification(
        user=supervisor,
        title=f"Neuer Änderungsantrag von {employee.get_full_name()}",
        message=f"{employee.get_full_name()} hat eine Arbeitszeitänderung für den {date_str} beantragt.",
        notification_type='info',
        reference_id=f"wscreq_{change_request.id}", # Eindeutiger Key
        link_to='admin-requests' 
    )


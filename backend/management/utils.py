def send_change_notification(change_request):
    from core.utils import create_notification
    
    # Sicherer Zugriff über die WorkSession, falls requested_by noch nicht in DB steht
    employee = change_request.worksession.work_day.employee
    
    # Datum formatieren
    date_str = change_request.worksession.work_day.date.strftime('%d.%m.%Y')
   
    create_notification(
        user=employee,
        title=f"Änderungsantrag für den {date_str} genehmigt.",
        message=f"{employee.supervisor} hat deinen Änderungsantrag für den {date_str} genehmigt.",
        notification_type='info',
        reference_id=f"a_wscreq_{change_request.id}", # Eindeutiger Key
        link_to='requests' 
    )
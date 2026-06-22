from rest_framework import serializers
from django.utils.timezone import localtime

class CalendarEventSerializer(serializers.Serializer):
    id = serializers.CharField()
    date = serializers.DateField()
    type = serializers.CharField()
    title = serializers.CharField()
    note = serializers.CharField(allow_blank=True, allow_null=True)
    status = serializers.CharField(required=False)
    isPending = serializers.BooleanField(default=False)
    isRequest = serializers.BooleanField(default=False)

    @staticmethod
    def from_workday(wd):
        """Transformiert einen WorkDay in ein Kalender-Event."""
        if wd.day_type == 'work':

            expected = float(wd.employee.get_expected_hours_for_date(wd.date))
            actual = float(wd.total_hours)

            diff = actual - expected
            # Vorzeichen für die Anzeige bestimmen
            prefix = "+" if diff > 0 else ""
            
            # Format: "8.00h (+0.50)" oder "7.50h (-0.50)"
            title = f"{actual:.2f}h ({prefix}{diff:.2f})"

            notes = [
                f"{localtime(s.check_in).strftime('%H:%M')} - "
                f"{localtime(s.check_out).strftime('%H:%M') if s.check_out else '...'}"
                for s in wd.sessions.all()
            ]
            note = " | ".join(notes)
        
        elif wd.day_type == 'vacation':
            title = wd.get_day_type_display()
            note = wd.note
    
        else:
            title = wd.get_day_type_display()
            note = ""

        return {
            "id": f"wd-{wd.id}",
            "date": wd.date,
            "type": wd.day_type,
            "title": title,
            "note": note,
            "status": "approved",
            "isPending": False,
            "isRequest": False,
        }

    @staticmethod
    def from_holiday(name, date):
        return {
            "title": name,
            "date": date.isoformat(),
            "type": "holiday"
            }

    @staticmethod
    def from_leave_request(lr, current_date):
        """Transformiert einen Tag eines LeaveRequests in ein Event."""
        return {
            "id": f"lr-{lr.id}-{current_date.isoformat()}",
            "date": current_date,
            "type": lr.leave_type,
            "title": f"{lr.get_leave_type_display()} (offen)",
            "note": lr.note or "",
            "status": lr.status,
            "isPending": lr.status == 'pending',
            "isRequest": True
        }
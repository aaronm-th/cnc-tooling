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
    
    # NEU: Strukturierte Felder für das schlanke Tooltip
    sessions = serializers.ListField(child=serializers.CharField(), required=False, allow_null=True)
    totalHours = serializers.CharField(required=False, allow_null=True)
    warning = serializers.CharField(required=False, allow_null=True)

    @staticmethod
    def from_workday(wd):
        """Transformiert einen WorkDay in ein Kalender-Event mit strukturierten Tooltip-Daten."""
        sessions_list = []
        has_auto_checkout = False

        # Sessions nur verarbeiten, wenn es ein gewöhnlicher Arbeitstag ist oder Sessions existieren
        if wd.sessions.exists():
            day_sessions = sorted(wd.sessions.all(), key=lambda s: s.check_in)
            for session in day_sessions:
                in_time = localtime(session.check_in).strftime("%H:%M")
                if session.check_out:
                    out_time = localtime(session.check_out).strftime("%H:%M")
                    auto_str = " (Auto-Checkout)" if getattr(session, 'is_auto_checkout', False) else ""
                    sessions_list.append(f"{in_time} - {out_time}{auto_str}")
                    
                    if getattr(session, 'is_auto_checkout', False):
                        has_auto_checkout = True
                else:
                    sessions_list.append(f"{in_time} - (offen)")

        # Gesamtarbeitsstunden nur bei Arbeitstagen mitsenden (bei Urlaub/Krankheit None)
        total_hours = None
        if wd.day_type == 'work' or wd.sessions.exists():
            total_hours = str(wd.total_hours)

        # Titel bestimmen
        if wd.day_type == 'work':
            title = "Arbeitstag"
        else:
            title = wd.get_day_type_display()

        return {
            "id": f"wd-{wd.id}",
            "date": wd.date,
            "type": wd.day_type,
            "title": title,
            "note": wd.note if wd.note else None,
            "sessions": sessions_list if sessions_list else None,
            "totalHours": total_hours,
            "warning": "Auto-Checkout erfolgt. Bitte Zeiten überprüfen!" if has_auto_checkout else None,
            "status": "approved",
            "isPending": False,
            "isRequest": False,
        }

    @staticmethod
    def from_holiday(name, date):
        return {
            "id": f"holiday-{date.isoformat()}",
            "title": name,
            "date": date.isoformat(),
            "type": "holiday",
            "note": None,
            "sessions": None,
            "totalHours": None,
            "warning": None
        }

    @staticmethod
    def from_leave_request(lr, current_date):
        """Transformiert einen Tag eines LeaveRequests in ein Event."""
        return {
            "id": f"lr-{lr.id}-{current_date.isoformat()}",
            "requestId": lr.id,         
            "date": current_date,
            "leave_start": lr.leave_start,   
            "leave_end": lr.leave_end,       
            "type": lr.leave_type,
            "title": f"{lr.get_leave_type_display()} (offen)",
            "note": lr.note if lr.note else None,
            "sessions": None,
            "totalHours": None,
            "warning": None,
            "status": lr.status,
            "isPending": lr.status == 'pending',
            "isRequest": True
        }
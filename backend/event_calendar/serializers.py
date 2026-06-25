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
            
            title = "Arbeitstag"

            # --- NEU: Chronologische Sortierung & Formatierung für das Tooltip ---
            day_sessions = sorted(wd.sessions.all(), key=lambda s: s.check_in)
            
            session_strings = []
            for session in day_sessions:
                in_time = localtime(session.check_in).strftime("%H:%M")
                if session.check_out:
                    out_time = localtime(session.check_out).strftime("%H:%M")
                    session_strings.append(f"{in_time} - {out_time}")
                else:
                    session_strings.append(f"{in_time} - (offen)")

            if session_strings:                
                # Wenn im Admin eine zusätzliche Notiz eingetragen wurde
                if wd.note:
                    session_strings.append(f"Notiz: {wd.note}")
                
                # Das 'TOTAL:'-Präfix für die Sonderbehandlung im Vue-Tooltip
                session_strings.append(f"TOTAL:Gesamtzeit: {wd.total_hours} Std.")
                
                note = "|".join(session_strings)
            else:
                note = wd.note if wd.note else ""
        
        elif wd.day_type == 'vacation':
            title = wd.get_day_type_display()
            note = wd.note
            
        else:
            title = wd.get_day_type_display()
            note = wd.note if wd.note else ""

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
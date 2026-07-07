from rest_framework import serializers

from attendance.models import WorkSession, WorkDay
from .models import EmployeeDocument
from datetime import date
from django.utils import timezone

import holidays


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    # NEU: Generiert die absolute URL zur Datei (oder nutzt alternativ deine Download-Route)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocument
        fields = [
            'id', 
            'document_type', 
            'document_type_display', 
            'original_filename', 
            'uploaded_at', 
            'employee_name',
            'file_url' # <-- Hier ergänzt
        ]

    def get_file_url(self, obj):
        # Falls du die Datei direkt über Medienspeicher streamen willst:
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(f"/api/documents/download/{obj.id}/")
        return None



class WorkSessionSerializer(serializers.ModelSerializer):
    """Minimaler Serializer für Sessions innerhalb eines Tages"""
    class Meta:
        model = WorkSession
        fields = ['check_in', 'check_out', 'duration_str']


class WorkDayWithSessionsSerializer(serializers.ModelSerializer):
    day_type_display = serializers.CharField(source='get_day_type_display', read_only=True)
    
    display_status = serializers.SerializerMethodField()
    session_details = serializers.SerializerMethodField()
    expected_hours = serializers.SerializerMethodField()
    actual_hours = serializers.SerializerMethodField()
    diff = serializers.SerializerMethodField()

    class Meta:
        model = WorkDay
        fields = [
            'date', 
            'day_type', 
            'day_type_display', 
            'expected_hours',
            'actual_hours',  # Komma ergänzt
            'diff',          # Komma ergänzt
            'display_status', 
            'session_details'
        ]


    def _get_raw_expected(self, obj):
        """Hilfsmethode für die reine Zahl"""
        return float(obj.employee.get_expected_hours_for_date(obj.date))

    def get_expected_hours(self, obj):
        return f"{self._get_raw_expected(obj):.2f}"

    def get_actual_hours(self, obj):
        # Absicherung: Falls total_hours None ist, nutzen wir 0.0
        hours = obj.total_hours if obj.total_hours is not None else 0.0
        return f"{float(hours):.2f}"

    def get_diff(self, obj):
        expected = self._get_raw_expected(obj)
        # Absicherung: Falls total_hours None ist, nutzen wir 0.0
        actual_hours = obj.total_hours if obj.total_hours is not None else 0.0
        actual = float(actual_hours)
        diff = actual - expected
        return f"{diff:+.2f}"

    def get_display_status(self, obj):
        # 1. Wenn Sessions existieren, ist er anwesend (egal ob Vergangenheit oder Zukunft)
        if obj.sessions.exists():
            return "Anwesend"
        
        # 2. Feiertags-Logik bleibt gleich
        if obj.day_type == WorkDay.DayType.HOLIDAY:
            de_holidays = holidays.Germany(prov='BW')
            return de_holidays.get(obj.date) or "Feiertag"
        
        # 3. ZUKUNFTS-CHECK für reguläre Arbeitstage
        if obj.day_type == WorkDay.DayType.WORK:
            if obj.date > date.today():
                return "Geplant"  # Oder "Offen" / "Arbeitstag"
            return "Fehlzeit"     # In der Vergangenheit war es eine Fehlzeit

        return obj.get_day_type_display()

    def get_session_details(self, obj):
        sessions = obj.sessions.all()
        if sessions.exists():
            formatted_sessions = []
            for s in sessions:
                # timezone.localtime() rechnet den UTC-Wert automatisch in die
                # Zeitzone um, die in deiner settings.py (TIME_ZONE) definiert ist.
                local_in = timezone.localtime(s.check_in) if s.check_in else None
                local_out = timezone.localtime(s.check_out) if s.check_out else None
                
                in_str = local_in.strftime('%H:%M') if local_in else '??'
                out_str = local_out.strftime('%H:%M') if local_out else '...'
                
                formatted_sessions.append(f"{in_str} - {out_str}")
                
            return " | ".join(formatted_sessions)

        if obj.day_type == WorkDay.DayType.HOLIDAY:
            de_holidays = holidays.Germany(prov='BW')
            return de_holidays.get(obj.date) or "Gesetzlicher Feiertag"
        
        if obj.date > date.today() and obj.day_type == WorkDay.DayType.WORK:
            return "Noch keine Buchungen"
            
        return "-"
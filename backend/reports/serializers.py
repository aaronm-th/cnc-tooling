from rest_framework import serializers

from attendance.models import WorkSession, WorkDay
from .models import EmployeeDocument

import holidays


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    # Gibt den lesbaren Namen des Choices-Feldes zurück (z.B. "Arbeitsvertrag")
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    # Name des Mitarbeiters für die UI
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)

    class Meta:
        model = EmployeeDocument
        fields = [
            'id', 
            'document_type', 
            'document_type_display', 
            'original_filename', 
            'uploaded_at', 
            'employee_name'
        ]



class WorkSessionSerializer(serializers.ModelSerializer):
    """Minimaler Serializer für Sessions innerhalb eines Tages"""
    class Meta:
        model = WorkSession
        fields = ['check_in', 'check_out', 'duration_str']


class WorkDayWithSessionsSerializer(serializers.ModelSerializer):
    day_type_display = serializers.CharField(source='get_day_type_display', read_only=True)
    
    display_date = serializers.SerializerMethodField()
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
            'display_date', 
            'display_status', 
            'session_details'
        ]

    def get_display_date(self, obj):
        # Wochentag abgekürzt + Datum
        return obj.date.strftime('%a, %d.%m.')

    def _get_raw_expected(self, obj):
        """Hilfsmethode für die reine Zahl"""
        return float(obj.employee.get_expected_hours_for_date(obj.date))

    def get_expected_hours(self, obj):
        return f"{self._get_raw_expected(obj):.2f}"

    def get_actual_hours(self, obj):
        # Nutzt das Property/Attribut vom Modell
        return f"{float(obj.total_hours):.2f}"

    def get_diff(self, obj):
        # Wichtig: Rechnen mit Zahlen, Rückgabe als formatierter String
        expected = self._get_raw_expected(obj)
        actual = float(obj.total_hours)
        diff = actual - expected # Meist ist Diff = Ist - Soll
        return f"{diff:+.2f}" # Das + zeigt explizit + oder - an

    def get_display_status(self, obj):
        if obj.sessions.exists():
            return "Anwesend"
        
        if obj.day_type == WorkDay.DayType.HOLIDAY:
            de_holidays = holidays.Germany(prov='BW')
            return de_holidays.get(obj.date) or "Feiertag"
        
        if obj.day_type == WorkDay.DayType.WORK:
            return "Fehlzeit" # Klingt etwas netter als Unentschuldigt

        return obj.get_day_type_display()

    def get_session_details(self, obj):
        sessions = obj.sessions.all()
        if sessions.exists():
            return " | ".join([
                f"{s.check_in.strftime('%H:%M') if s.check_in else '??'} - "
                f"{s.check_out.strftime('%H:%M') if s.check_out else '...'}" 
                for s in sessions
            ])

        if obj.day_type == WorkDay.DayType.HOLIDAY:
            de_holidays = holidays.Germany(prov='BW')
            return de_holidays.get(obj.date) or "Gesetzlicher Feiertag"
        
        return "-"
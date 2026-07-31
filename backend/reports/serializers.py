from rest_framework import serializers
from attendance.models import WorkDay
from .models import EmployeeDocument
from core.models import Employee, MonthlyPayout
from django.db.models import Sum
from datetime import date
from django.utils import timezone
import holidays

# --- 1. Bestehende Serializer (Bleiben unverändert wie in deiner Datei) ---

class EmployeeDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    employee_name = serializers.CharField(source='employee.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocument
        fields = ['id', 'document_type', 'document_type_display', 'original_filename', 'uploaded_at', 'employee_name', 'file_url']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(f"/api/documents/download/{obj.id}/")
        return None


class AdminMonthlyReportOverviewSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)
    username = serializers.CharField(read_only=True)
    avatar = serializers.SerializerMethodField()
    
    # Die Kernfelder für deine Übersichtstabelle
    ist_hours = serializers.SerializerMethodField()
    soll_hours = serializers.SerializerMethodField()
    is_processed = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ['id', 'name', 'username', 'initials', 'avatar', 'ist_hours', 'soll_hours', 'is_processed']

    def _get_payout(self, obj):
        """Hilfsmethode zur Vermeidung von Doppelabfragen pro Zeile."""
        if not hasattr(self, '_payout_cache'):
            self._payout_cache = {}
            
        year = self.context.get('year')
        month = self.context.get('month')
        cache_key = f"{obj.id}_{year}_{month}"
        
        if cache_key not in self._payout_cache:
            self._payout_cache[cache_key] = MonthlyPayout.objects.filter(
                employee=obj, year=year, month=month, is_processed=True
            ).first()
            
        return self._payout_cache[cache_key]

    def get_is_processed(self, obj) -> bool:
        return self._get_payout(obj) is not None

    def get_ist_hours(self, obj) -> float:
        payout = self._get_payout(obj)
        if payout:
            return float(payout.worked_hours) # Nutzt fixierten Wert
            
        # Fallback auf Live-Berechnung deiner Modell-Methode
        year = self.context.get('year')
        month = self.context.get('month')
        stats = obj.get_hours_balance_for_month(year, month)
        return float(stats["worked"])

    def get_soll_hours(self, obj) -> float:
        payout = self._get_payout(obj)
        if payout:
            return float(payout.expected_hours) # Nutzt fixierten Wert
            
        # Fallback auf Live-Berechnung
        year = self.context.get('year')
        month = self.context.get('month')
        stats = obj.get_hours_balance_for_month(year, month)
        return float(stats["expected"])

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.get_photo_url() if hasattr(obj, 'get_photo_url') else None


class WorkDayWithSessionsSerializer(serializers.ModelSerializer):
    """
    Bereitet einen einzelnen Tag exakt so vor, wie das Schleifen-Array im jspdf-Service
    es für das Tabellenraster erwartet.
    """
    actual_hours = serializers.ReadOnlyField(source='total_hours')
    diff = serializers.SerializerMethodField() 
    session_details = serializers.SerializerMethodField()
    day_type_display = serializers.SerializerMethodField()

    class Meta:
        model = WorkDay
        fields = ['id', 'date', 'day_type', 'day_type_display', 'actual_hours', 'diff', 'session_details']

    def get_diff(self, obj):
        if obj.day_type in [WorkDay.DayType.VACATION, WorkDay.DayType.SICK]:
            return 0.0

        ist = float(obj.total_hours or 0.0)

        # Feiertag/Wochenende OHNE geleistete Stunden: kein Soll erwartet, Saldo bleibt 0.
        # Wurde trotzdem gearbeitet, zählt es ganz normal als Plusstunden.
        if obj.day_type in [WorkDay.DayType.HOLIDAY, WorkDay.DayType.WEEKEND] and ist == 0:
            return 0.0

        soll = 0.0
        if obj.employee and hasattr(obj.employee, 'get_expected_hours_for_date'):
            soll = float(obj.employee.get_expected_hours_for_date(obj.date) or 0.0)
        else:
            soll = 8.0

        return round(ist - soll, 2)

    def get_day_type_display(self, obj):
        today = timezone.localdate()
        
        # Logik für reguläre Arbeitstage
        if obj.day_type == WorkDay.DayType.WORK:
            if obj.date > today:
                return "Geplant"
            
            # Wenn in der Vergangenheit, aber keine Einstempelungen vorhanden sind
            if not obj.sessions.exists():
                return "Fehlzeit"
                
            return "Arbeitstag"
            
        # Für alle Sonderfälle (Urlaub, Krank, Wochenende, Feiertag) nutzen wir die Django-Übersetzung
        return obj.get_day_type_display()

    def get_session_details(self, obj):
        today = timezone.localdate()
        sessions = obj.sessions.all()
        
        # 1. Wenn Stempelzeiten existieren, listen wir diese IMMER auf (auch am Wochenende)
        if sessions.exists():
            formatted_sessions = []
            for s in sessions:
                local_in = timezone.localtime(s.check_in) if s.check_in else None
                local_out = timezone.localtime(s.check_out) if s.check_out else None
                
                in_str = local_in.strftime('%H:%M') if local_in else '??'
                out_str = local_out.strftime('%H:%M') if local_out else '...'
                formatted_sessions.append(f"{in_str} - {out_str}")
            return " | ".join(formatted_sessions)

        # 2. Wenn keine Sessions existieren, bestimmen wir den Text anhand des Typs und Datums
        if obj.day_type == WorkDay.DayType.HOLIDAY:
            de_holidays = holidays.Germany(prov='BW')
            return de_holidays.get(obj.date) or "Gesetzlicher Feiertag"
        
        if obj.day_type == WorkDay.DayType.WEEKEND:
            return "Wochenende"

        if obj.day_type in [WorkDay.DayType.VACATION, WorkDay.DayType.SICK]:
            return obj.get_day_type_display()

        # Typ ist WORK, aber es gibt keine Sessions
        if obj.date > today:
            return "Geplant"

        return "Keine Einträge (Fehlzeit)"


class EmployeeMonthlyReportDetailSerializer(serializers.ModelSerializer):
    """
    Der universelle Detail-Serializer für die PDF-Daten-Generierung.
    Nutzt nun für das Monats-Ist ebenfalls die tagesgenaue Soll-Berechnung bei Fehlzeiten.
    """
    userName = serializers.CharField(source='get_full_name', read_only=True)
    monthName = serializers.SerializerMethodField()
    year = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()

    monthly_soll = serializers.SerializerMethodField()
    monthly_ist = serializers.SerializerMethodField()
    monthly_diff = serializers.SerializerMethodField()
    
    events = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ['id', 'userName', 'monthName', 'year', 'monthly_soll', 'monthly_ist', 'monthly_diff', 'events', 'is_locked']

    def get_monthName(self, obj):
        months_de = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
        month = self.context.get('month', 1)
        return months_de[month]

    def get_year(self, obj):
        return str(self.context.get('year', date.today().year))

    def get_is_locked(self, obj):
        return self.context.get('is_locked', False)
    
    def get_monthly_soll(self, obj):
        return round(obj.get_expected_hours_for_month(self.context.get('year'), self.context.get('month')), 2)

    def get_monthly_ist(self, obj):
        year = self.context.get('year')
        month = self.context.get('month')
        workdays = WorkDay.objects.filter(employee=obj, date__year=year, date__month=month)
        
        ist_sum = 0.0
        for day in workdays:
            # Bei genehmigten Fehlzeiten (Urlaub, Krankheit, Feiertag) rechnen wir 
            # das tagesgenaue Soll als geleistet an, damit kein Monats-Minus entsteht:
            if day.day_type in [WorkDay.DayType.VACATION, WorkDay.DayType.SICK, WorkDay.DayType.HOLIDAY]:
                if hasattr(obj, 'get_expected_hours_for_date'):
                    ist_sum += float(obj.get_expected_hours_for_date(day.date) or 0.0)
                else:
                    ist_sum += 8.0
            else:
                ist_sum += float(day.total_hours or 0.0)
                
        return round(ist_sum, 2)

    def get_monthly_diff(self, obj):
        return round(self.get_monthly_ist(obj) - self.get_monthly_soll(obj), 2)

    def get_events(self, obj):
        year = self.context.get('year')
        month = self.context.get('month')
        
        workdays = WorkDay.objects.filter(
            employee=obj,
            date__year=year,
            date__month=month
        ).order_by('date')
        
        return WorkDayWithSessionsSerializer(workdays, many=True, context=self.context).data






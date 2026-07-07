from rest_framework import serializers
from attendance.models import WorkDay
from .models import EmployeeDocument
from core.models import Employee
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
    soll_hours = serializers.SerializerMethodField()
    ist_hours = serializers.SerializerMethodField()
    diff_hours = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ['id', 'name', 'username', 'initials', 'soll_hours', 'ist_hours', 'diff_hours']

    def get_initials(self, obj):
        f = obj.first_name[0] if obj.first_name else ""
        l = obj.last_name[0] if obj.last_name else ""
        return f"{f}{l}".upper() or "MA"

    def get_soll_hours(self, obj):
        year = self.context.get('year')
        month = self.context.get('month')
        return round(obj.get_expected_hours_for_month(year, month), 2)

    def get_ist_hours(self, obj):
        year = self.context.get('year')
        month = self.context.get('month')
        workdays = WorkDay.objects.filter(employee=obj, date__year=year, date__month=month)
        ist_sum = sum(day.total_hours for day in workdays)
        return round(float(ist_sum), 2)

    def get_diff_hours(self, obj):
        return round(self.get_ist_hours(obj) - self.get_soll_hours(obj), 2)


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
        # 1. Wenn es sich um ein Wochenende oder einen gesetzlichen Feiertag handelt,
        #    darf kein Minus entstehen -> Saldo bleibt glatt bei 0.00 h.
        #    (Hinweis: Falls bei dir 'weekend' / 'holiday' im Modell großgeschrieben sind, 
        #    passe die Strings hier entsprechend an, z.B. WorkDay.DayType.WEEKEND)
        if obj.day_type in [WorkDay.DayType.HOLIDAY, WorkDay.DayType.WEEKEND]:
            return 0.0
            
        # 2. Wenn der Mitarbeiter im Urlaub oder krank gemeldet ist, gilt die Fehlzeit
        #    als "Soll erfüllt" -> Saldo ist ebenfalls 0.00 h, damit kein fälschliches Minus entsteht.
        if obj.day_type in [WorkDay.DayType.VACATION, WorkDay.DayType.SICK]:
            return 0.0

        # 3. Regulärer Arbeitstag: Ist-Stunden holen
        ist = float(obj.total_hours or 0.0)

        # 4. Soll-Stunden exakt über deine Employee-Property für dieses Datum ermitteln!
        soll = 0.0
        if obj.employee and hasattr(obj.employee, 'get_expected_hours_for_date'):
            soll = float(obj.employee.get_expected_hours_for_date(obj.date) or 0.0)
        else:
            soll = 8.0 # Sicherer Fallback, falls die Property mal nicht greift

        return round(ist - soll, 2)

    def get_day_type_display(self, obj):
        if obj.day_type == WorkDay.DayType.WORK:
            if obj.date > date.today():
                return "Geplant"
            return "Fehlzeit"
        return obj.get_day_type_display()

    def get_session_details(self, obj):
        sessions = obj.sessions.all()
        if sessions.exists():
            formatted_sessions = []
            for s in sessions:
                local_in = timezone.localtime(s.check_in) if s.check_in else None
                local_out = timezone.localtime(s.check_out) if s.check_out else None
                
                in_str = local_in.strftime('%H:%M') if local_in else '??'
                out_str = local_out.strftime('%H:%M') if local_out else '...'
                formatted_sessions.append(f"{in_str} - {out_str}")
            return " | ".join(formatted_sessions)

        if obj.day_type == WorkDay.DayType.HOLIDAY:
            de_holidays = holidays.Germany(prov='BW')
            return de_holidays.get(obj.date) or "Gesetzlicher Feiertag"
        
        if obj.date > date.today():
            return "Geplant"
        
        if obj.day_type == WorkDay.DayType.WEEKEND:
            return "Wochenende"

        if obj.day_type in [WorkDay.DayType.VACATION, WorkDay.DayType.SICK]:
            return obj.get_day_type_display()

        return "Fehlzeit"


class EmployeeMonthlyReportDetailSerializer(serializers.ModelSerializer):
    """
    Der universelle Detail-Serializer für die PDF-Daten-Generierung.
    Nutzt nun für das Monats-Ist ebenfalls die tagesgenaue Soll-Berechnung bei Fehlzeiten.
    """
    userName = serializers.CharField(source='get_full_name', read_only=True)
    monthName = serializers.SerializerMethodField()
    year = serializers.SerializerMethodField()
    
    monthly_soll = serializers.SerializerMethodField()
    monthly_ist = serializers.SerializerMethodField()
    monthly_diff = serializers.SerializerMethodField()
    
    events = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ['id', 'userName', 'monthName', 'year', 'monthly_soll', 'monthly_ist', 'monthly_diff', 'events']

    def get_monthName(self, obj):
        months_de = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
        month = self.context.get('month', 1)
        return months_de[month]

    def get_year(self, obj):
        return str(self.context.get('year', date.today().year))

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






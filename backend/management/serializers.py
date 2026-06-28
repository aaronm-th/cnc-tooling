from rest_framework import serializers

from django.utils import timezone
import datetime

from attendance.models import LeaveRequest, WSChangeRequest, WorkSession, WorkDay
from core.models import Employee, VacationQuota
from core.services.vacation_service import VacationService

from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404


# --- NEU: URALUBS-QUOTA PREVIEW / ANZEIGE ---
class VacationQuotaSummarySerializer(serializers.ModelSerializer):
    vacation_left = serializers.SerializerMethodField()
    vacation_days_per_year = serializers.FloatField(source='total_days')

    class Meta:
        model = VacationQuota
        fields = ['vacation_days_per_year', 'vacation_left']

    def get_vacation_left(self, obj):
        current_year = timezone.now().year
        used_days = VacationService.get_used_days(obj.employee, current_year)
        total_available = float(obj.total_days) + float(obj.carried_over)
        return total_available - used_days


# --- NEU: SERIALIZER FÜR LISTE & DASHBOARD STATS ---
class TeamMemberSummarySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)
    username = serializers.CharField(read_only=True)
    avatar = serializers.SerializerMethodField()
    status_text = serializers.SerializerMethodField()
    overtime_hours = serializers.SerializerMethodField()
    
    # Die neuen, vereinfachten Urlaubsfelder
    vacation_total = serializers.SerializerMethodField()
    vacation_used = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'username', 'first_name', 'last_name', 'email', 'initials',
            'avatar', 'status_text', 'vacation_total', 'vacation_used', 
            'overtime_hours', 'weekly_hours', 'joined_at'
        ]

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.get_photo_url() if hasattr(obj, 'get_photo_url') else None

    def get_status_text(self, obj):
        return "Anwesend" if obj.status else "Abwesend"

    def get_overtime_hours(self, obj):
        return round(obj.overtime_balance, 2)

    def get_vacation_total(self, obj):
        """Holt den (falls nötig anteiligen) Jahresanspruch."""
        current_year = timezone.now().year
        return float(VacationService.get_total_days_for_year(obj, current_year))

    def get_vacation_used(self, obj):
        """Holt die verbrauchten Tage im aktuellen Jahr."""
        current_year = timezone.now().year
        return VacationService.get_used_days(obj, current_year)


# --- NEU: SERIALIZER FÜR DETAIL-ANSICHT & UPDATE (PUT/PATCH) ---
class TeamMemberDetailSerializer(TeamMemberSummarySerializer):
    vacation_days_per_year = serializers.FloatField(write_only=True, required=False)
    joined_at = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = Employee
        fields = TeamMemberSummarySerializer.Meta.fields + ['work_days_schema', 'is_active', 'vacation_days_per_year']
        read_only_fields = ['id', 'name', 'first_name', 'last_name', 'initials', 'avatar', 'status_text']

    def update(self, instance, validated_data):
        # 1. Felder auf dem Employee updaten
        instance = super().update(instance, validated_data)
        
        # 2. Quota für das aktuelle Kalenderjahr synchronisieren
        current_year = timezone.now().year
        current_year = timezone.now().year
        allocated_days = VacationService.get_total_days_for_year(instance, current_year)
        
        VacationQuota.objects.update_or_create(
            employee=instance,
            year=current_year,
            defaults={'total_days': allocated_days}
        )
        return instance


# --- BESTEHENDE SERIALIZER (ABGESTIMMT) ---
class LeaveRequestSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source='employee.name')
    initials = serializers.ReadOnlyField(source='employee.initials')
    avatar = serializers.SerializerMethodField()
    leave_start = serializers.DateField(format="%d.%m.%Y")
    leave_end = serializers.DateField(format="%d.%m.%Y")
    duration = serializers.ReadOnlyField(source='num_vacdays')
    request_date = serializers.DateTimeField(format="%d.%m.%Y, %H:%M")
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'name', 'initials', 'avatar', 'leave_type', 'leave_type_display', 
            'status', 'status_display', 'leave_start', 'leave_end', 'duration',
            'note', 'request_date'
        ]

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.employee.photo and request:
            return request.build_absolute_uri(obj.employee.photo.url)
        return None


class ChangeRequestSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source='requested_by.name')
    initials = serializers.ReadOnlyField(source='requested_by.initials')
    avatar = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    old_check_in = serializers.DateTimeField(format="%H:%M", allow_null=True)
    old_check_out = serializers.DateTimeField(format="%H:%M", allow_null=True)
    requested_check_in = serializers.DateTimeField(format="%H:%M")
    requested_check_out = serializers.DateTimeField(format="%H:%M")
    request_date = serializers.DateTimeField(format="%d.%m.%Y, %H:%M")
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    time_diff = serializers.SerializerMethodField()
    old_ver_exists = serializers.SerializerMethodField()

    class Meta:
        model = WSChangeRequest
        fields = [
            'id', 'name', 'initials', 'avatar', 'status', 'status_display', 
            'old_check_in', 'old_check_out', 'requested_check_in', 'requested_check_out',
            'employee_note', 'request_date', 'date', 'time_diff', 'old_ver_exists'
        ]

    def get_date(self, obj):
        return obj.work_day.date.strftime("%d.%m.%Y")

    def get_old_ver_exists(self, obj):
        return obj.worksession.old_ver_exists if obj.worksession else False

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.requested_by.photo and request:
            return request.build_absolute_uri(obj.requested_by.photo.url)
        return None
    
    def get_time_diff(self, obj):
        diff_min = obj.duration_difference / 60
        return f"{'+' if diff_min > 0 else ''}{diff_min:.0f} min"


class CreateEditEmployeeSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    work_days_schema = serializers.JSONField(required=False, default=dict)
    vacation_days_per_year = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=30.0)
    joined_at = serializers.DateField(required=False)

    def validate(self, attrs):
        """
        Objektübergreifende Validierung: Verhindert, dass ein Mitarbeiter 
        mit exakt demselben Vor- und Nachnamen doppelt angelegt wird.
        """
        first_name = attrs.get('first_name')
        last_name = attrs.get('last_name')

        # Falls wir im "Edit"-Modus sind, müssen wir die ID ignorieren (falls vorhanden im Kontext)
        # Für reine Create-Views reicht dieser einfache Check:
        if Employee.objects.filter(first_name=first_name, last_name=last_name, is_active=True).exists():
            raise serializers.ValidationError({
                "last_name": "Ein aktiver Mitarbeiter mit diesem Vor- und Nachnamen existiert bereits."
            })
            
        return attrs

    def validate_work_days_schema(self, value):
        if isinstance(value, dict):
            return {str(k): v for k, v in value.items()}
        return value
    

class ManualEntrySerializer(serializers.Serializer):
    ENTRY_TYPES = (
        ('vacation', 'Urlaub'),
        ('sick', 'Krankheit'),
        ('work', 'Zeiterfassung'),
    )

    member_id = serializers.IntegerField(write_only=True)
    type = serializers.ChoiceField(choices=ENTRY_TYPES)
    date = serializers.DateField()
    note = serializers.CharField(style={'base_template': 'textarea.html'})
    
    hours_or_days = serializers.FloatField(required=False, min_value=0.0)
    check_in = serializers.TimeField(required=False, allow_null=True)
    check_out = serializers.TimeField(required=False, allow_null=True)

    def validate(self, attrs):
        entry_type = attrs.get('type')
        date_obj = attrs.get('date')
        
        employee = get_object_or_404(Employee, id=attrs.get('member_id'))
        self.context['employee_instance'] = employee

        # NEU: Validierung gegen das Eintrittsdatum (joined_at)
        if employee.joined_at and date_obj < employee.joined_at:
            # Formatiere das Datum für eine lesbare Fehlermeldung
            joined_formatted = employee.joined_at.strftime('%d.%m.%Y')
            raise serializers.ValidationError({
                "date": _(f"Einträge vor dem Eintrittsdatum ({joined_formatted}) sind nicht erlaubt.")
            })

        # Bei Urlaub/Krankheit löschen wir eventuelle Zeiteingaben aus dem Frontend
        if entry_type in ['vacation', 'sick']:
            attrs['check_in'] = None
            attrs['check_out'] = None

        # Bei der Zeiterfassung validieren wir die korrekte Uhrzeit
        elif entry_type == 'work':
            check_in = attrs.get('check_in')
            check_out = attrs.get('check_out')

            if not check_in or not check_out:
                raise serializers.ValidationError({"check_in": _("Kommen- und Gehen-Zeiten sind erforderlich.")})
            if check_in >= check_out:
                raise serializers.ValidationError({"check_out": _("Die Gehen-Zeit muss nach der Kommen-Zeit liegen.")})
            
            attrs['hours_or_days'] = None

        return attrs

    def create(self, validated_data):
        employee = self.context['employee_instance']
        entry_type = validated_data['type']
        date_obj = validated_data['date']
        note = validated_data['note']
        supervisor = self.context['request'].user

        # 1. WorkDay holen oder erstellen
        work_day, created = WorkDay.objects.get_or_create(
            employee=employee, 
            date=date_obj,
            defaults={'day_type': entry_type, 'note': f"[{supervisor.get_full_name()}]: {note}"}
        )
        
        # Falls der Tag bereits existierte, erzwingen wir das harte Überschreiben
        if not created:
            work_day.day_type = entry_type
            work_day.note = f"[{supervisor.get_full_name()}]: {note}"
            work_day.save()

        # 2. RADIKAL AUFRÄUMEN: Unabhängig vom Typ löschen wir alle alten Sessions dieses Tages.
        # - Verhindert das Aufaddieren bei erneuter Zeiterfassung ('work' -> 'work')
        # - Bereinigt alte Sessions, falls ein Arbeitstag zu Urlaub/Krank umgebucht wird ('work' -> 'vacation')
        work_day.sessions.all().delete()

        # 3. Nur wenn der neue Typ 'work' ist, erstellen wir die EINE, neue korrekte Session
        if entry_type == 'work':
            naive_check_in = datetime.datetime.combine(date_obj, validated_data['check_in'])
            naive_check_out = datetime.datetime.combine(date_obj, validated_data['check_out'])
            
            current_tz = timezone.get_current_timezone()
            aware_check_in = timezone.make_aware(naive_check_in, current_tz)
            aware_check_out = timezone.make_aware(naive_check_out, current_tz)

            WorkSession.objects.create(
                work_day=work_day,
                check_in=aware_check_in,
                check_out=aware_check_out
            )
            
        return validated_data

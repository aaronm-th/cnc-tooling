from rest_framework import serializers
from django.utils import timezone
from attendance.models import LeaveRequest, WSChangeRequest
from core.models import Employee, VacationQuota
from core.services.vacation_service import VacationService


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
    avatar = serializers.SerializerMethodField()
    status_text = serializers.SerializerMethodField()
    vacation_left = serializers.SerializerMethodField()
    vacation_days_per_year = serializers.SerializerMethodField()
    overtime_hours = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'first_name', 'last_name', 'email', 'initials',
            'avatar', 'status_text', 'vacation_left', 'vacation_days_per_year', 
            'overtime_hours', 'weekly_hours', 'joined_at'
        ]

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.get_photo_url() if hasattr(obj, 'get_photo_url') else None

    def get_status_text(self, obj):
        return "Anwesend" if obj.status else "Abwesend"

    def _get_current_quota(self, obj):
        current_year = timezone.now().year
        quota, _ = VacationQuota.objects.get_or_create(
            employee=obj,
            year=current_year,
            defaults={'total_days': VacationService.calculate_initial_quota(obj, current_year)}
        )
        return quota

    def get_vacation_left(self, obj):
        quota = self._get_current_quota(obj)
        used_days = VacationService.get_used_days(obj, quota.year)
        return (float(quota.total_days) + float(quota.carried_over)) - used_days

    def get_vacation_days_per_year(self, obj):
        return float(self._get_current_quota(obj).total_days)

    def get_overtime_hours(self, obj):
        return round(obj.overtime_balance, 2)


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
        allocated_days = VacationService.calculate_initial_quota(instance, current_year)
        
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


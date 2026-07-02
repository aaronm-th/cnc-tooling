from .models import LeaveRequest, WorkSession
from rest_framework import serializers
from core.models import VacationQuota
from .models import WorkSession, WSChangeRequest
from datetime import timedelta
from core.services.vacation_service import VacationService

class LeaveRequestSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_count = serializers.IntegerField(source='num_vacdays', read_only=True)
    reviewed_by = serializers.ReadOnlyField(source='reviewed_by.get_full_name')

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'request_date', 'leave_start', 'leave_end', 
            'leave_type', 'type_display', 'status', 'status_display', 
            'days_count', 'note', 'reviewed_date', 'reviewed_by'
        ]
        read_only_fields = ['id', 'request_date', 'status']

    def validate(self, data):
        employee = self.context['request'].user
        start = data.get('leave_start')
        end = data.get('leave_end')
        leave_type = data.get('leave_type')

        joined_at = getattr(employee, 'joined_at', None) 
        
        if joined_at and start and start < joined_at:
            raise serializers.ValidationError(
                {"leave_start": f"Der Urlaubsbeginn darf nicht vor dem Eintrittsdatum ({joined_at.strftime('%d.%m.%Y')}) liegen."}
            )

        if start and end:
            has_workday = False
            current_date = start
            while current_date <= end:
                if current_date.weekday() < 5:
                    has_workday = True
                    break
                current_date += timedelta(days=1)
            
            if not has_workday:
                raise serializers.ValidationError(
                    {"leave_start": "Der gewählte Zeitraum enthält keine Arbeitstage (nur Wochenende)."}
                )

        # --- Bestehende Urlaubs-Quoten Prüfung ---
        if leave_type == 'vacation':
            quota, _ = VacationQuota.objects.get_or_create(
                employee=employee, year=start.year
            )
            # Nutze eine Hilfsmethode oder temporäre Berechnung
            # (Annahme: num_vacdays ist eine Methode im Model)
            temp_leave = LeaveRequest(
                leave_start=start, 
                leave_end=end,
                leave_type=leave_type
            )

            remaining_days = quota.total_days -  VacationService.get_used_days(employee, start.year)

            if temp_leave.num_vacdays() > remaining_days:
                raise serializers.ValidationError(
                    {"leave_type": f"Guthaben reicht nicht aus (Benötigt: {temp_leave.num_vacdays()}, Verfügbar: {remaining_days})."}
                )
        
        return data
    

class WorkSessionSerializer(serializers.ModelSerializer):
    duration = serializers.ReadOnlyField(source='duration_str') 
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = WorkSession
        fields = ['id', 'check_in', 'check_out', 'duration', 'is_active']

    def get_is_active(self, obj):
        return obj.check_out is None


class WSChangeRequestSerializer(serializers.ModelSerializer):
    """
    Serializer für Korrekturanträge. 
    Wird sowohl für Korrekturen (mit Session) als auch Neuanlagen (ohne Session) genutzt.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by = serializers.ReadOnlyField(source='reviewed_by.get_full_name')

    
    class Meta:
        model = WSChangeRequest
        fields = [
            'id', 
            'employee_note',
            'request_date', 
            'requested_check_in', 
            'requested_check_out', 
            'status',
            'status_display',
            'old_check_in',
            'old_check_out',
            'reviewed_date', 
            'reviewed_by'
        ]
        read_only_fields = ['id', 'status', 'old_check_in', 'old_check_out']


class WorkSessionDetailSerializer(serializers.ModelSerializer):
    """
    Detail-Serializer für die Anzeige im Frontend-Modal.
    """
    pending_request = serializers.SerializerMethodField()
    date = serializers.DateField(source='work_day.date', read_only=True)
    duration = serializers.ReadOnlyField(source='duration_str')

    class Meta:
        model = WorkSession
        fields = [
            'id', 
            'check_in', 
            'check_out', 
            'duration', 
            'pending_request', 
            'date'
        ]

    def get_pending_request(self, obj):
        # Nutzt den related_name 'change_requests' aus deinem Model
        request = obj.change_requests.filter(status='pending').first()
        if request:
            return WSChangeRequestSerializer(request).data
        return None
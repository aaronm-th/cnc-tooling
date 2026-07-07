from rest_framework import serializers
from attendance.models import LeaveRequest, WSChangeRequest



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

    class Meta:
        model = WSChangeRequest
        fields = [
            'id', 'name', 'initials', 'avatar', 'status', 'status_display', 
            'old_check_in', 'old_check_out', 'requested_check_in', 'requested_check_out',
            'employee_note', 'request_date', 'date', 'time_diff'
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
        diff_min = obj.duration_difference_minutes
        return f"{'+' if diff_min > 0 else ''}{diff_min:.0f} min"
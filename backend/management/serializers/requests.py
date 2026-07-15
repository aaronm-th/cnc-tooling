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



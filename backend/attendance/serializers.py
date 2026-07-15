from datetime import timedelta
from rest_framework import serializers

# Core Services & Models
from core.models import VacationQuota, first_locked_month, is_month_locked
from core.services.vacation_service import VacationService

from django.core.exceptions import ValidationError as DjangoValidationError

# Local Models
from .models import LeaveRequest, WorkSession, WSChangeRequest
from core.models import Employee


class RequesterSerializer(serializers.ModelSerializer):

    """Hilfs-Serializer für die Anzeige von Antragssteller-Details."""
    name = serializers.CharField(source='get_full_name', read_only=True)
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'username', 'initials', 'avatar'
        ]

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.get_photo_url() if hasattr(obj, 'get_photo_url') else None


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
        
        # 1. Temporäre Modellinstanz für die Model-Clean-Validierung erstellen
        # Bei einem Update (self.instance existiert) mischen wir die bestehenden Daten mit den neuen
        instance = self.instance or LeaveRequest(employee=employee)
        
        # Bei einem Update den Employee sicherstellen, bei Neuanlage zuweisen
        instance.employee = employee 
        
        # Neue Werte aus dem Request temporär auf die Instanz schreiben
        for key, value in data.items():
            setattr(instance, key, value)

        try:
            # Hier triggern wir Djangos Model-clean() (Vergangenheits-Check, Überlappung, joined_at)
            instance.full_clean()
        except DjangoValidationError as exc:
            # Django-Fehlermeldungen abfangen und in DRF ValidationError konvertieren
            # Wir packen globale Fehler in 'non_field_errors'
            error_messages = exc.message_dict.get('__all__', [str(exc)])
            raise serializers.ValidationError({"non_field_errors": error_messages})

        # --- Deine bestehenden zusätzlichen API-Validierungen (können so bleiben) ---
        start = data.get('leave_start', getattr(self.instance, 'leave_start', None))
        end = data.get('leave_end', getattr(self.instance, 'leave_end', None))
        leave_type = data.get('leave_type', getattr(self.instance, 'leave_type', None))

        # (Der joined_at Check wurde ins Model verlagert, kann hier theoretisch entfallen, 
        # schadet als doppelter Boden aber auch nicht)
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

            # NEU: Monatssperre – verhindert, dass ein Mitarbeiter überhaupt
            # einen Antrag für einen bereits abgeschlossenen Monat anlegt
            # oder nachträglich in einen gesperrten Monat verschiebt.
            locked_month = first_locked_month(employee, start, end)
            if locked_month:
                raise serializers.ValidationError(
                    {"leave_start": f"Der Monat {locked_month.strftime('%m/%Y')} ist bereits abgeschlossen. "
                                      "Für diesen Zeitraum kann kein Antrag mehr gestellt werden."}
                )

        # --- Bestehende Urlaubs-Quoten Prüfung ---
        if leave_type == 'vacation' and start and end:
            quota, _ = VacationQuota.objects.get_or_create(
                employee=employee, year=start.year
            )
            
            # Wir nutzen direkt die valide temporäre Instanz von oben
            remaining_days = quota.total_days - VacationService.get_used_days(employee, start.year)

            if instance.num_vacdays() > remaining_days:
                raise serializers.ValidationError(
                    {"leave_type": f"Guthaben reicht nicht aus (Benötigt: {instance.num_vacdays()}, Verfügbar: {remaining_days})."}
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
    time_diff = serializers.SerializerMethodField()
    requester = RequesterSerializer(source='requested_by', read_only=True)
    
    class Meta:
        model = WSChangeRequest
        fields = [
            'id', 
            'work_day',
            'employee_note',
            'request_date', 
            'requested_check_in', 
            'requested_check_out', 
            'status',
            'status_display',
            'old_check_in',
            'old_check_out',
            'reviewed_date', 
            'reviewed_by',
            'requester',
            'time_diff'
        ]
        read_only_fields = ['id', 'status', 'old_check_in', 'old_check_out', 'work_day']

    def get_time_diff(self, obj):
        diff_min = obj.duration_difference_minutes
        return f"{'+' if diff_min > 0 else ''}{diff_min:.0f} min"

    def validate(self, attrs):
        instance = self.instance or WSChangeRequest()
        
        for key, value in attrs.items():
            setattr(instance, key, value)
            
        request = self.context.get('request')
        if request:
            instance.requested_by = request.user
            
        # NEU: Den work_day aus dem Serializer-Kontext an die Instanz heften
        work_day = self.context.get('work_day')
        if work_day:
            instance.work_day = work_day

        # NEU: worksession ebenfalls aus dem Context ziehen, sonst schließt
        # clean() die eigene Session bei der Überlappungsprüfung nicht aus.
        worksession = self.context.get('worksession')
        if worksession:
            instance.worksession = worksession

        # NEU: Monatssperre – verhindert, dass überhaupt ein neuer
        # Korrekturantrag für einen abgeschlossenen Monat gestellt/geändert
        # werden kann (unabhängig davon, ob er später genehmigt würde).
        if instance.work_day and is_month_locked(instance.work_day.employee, instance.work_day.date):
            raise serializers.ValidationError({
                "non_field_errors": [
                    f"Der Monat {instance.work_day.date.strftime('%m/%Y')} ist bereits abgeschlossen "
                    "und kann nicht mehr bearbeitet werden."
                ]
            })
        
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            error_messages = exc.message_dict.get('__all__', [str(exc)])
            raise serializers.ValidationError({"non_field_errors": error_messages})
            
        return attrs
        

class WorkSessionDetailSerializer(serializers.ModelSerializer):
    """
    Detail-Serializer für die Anzeige im Frontend-Modal.
    """
    pending_requests = serializers.SerializerMethodField()
    date = serializers.DateField(source='work_day.date', read_only=True)
    duration = serializers.ReadOnlyField(source='duration_str')

    class Meta:
        model = WorkSession
        fields = [
            'id', 
            'check_in', 
            'check_out', 
            'duration', 
            'pending_requests', 
            'date'
        ]

    def get_pending_requests(self, obj):
        # Nutzt den related_name 'change_requests' aus deinem Model
        requests = obj.change_requests.filter(status='pending')
        if requests:
            return WSChangeRequestSerializer(requests, many=True).data
        return None

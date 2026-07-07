from rest_framework import serializers
from django.utils import timezone
from core.models import Employee, VacationQuota
from core.services.vacation_service import VacationService


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
            'avatar', 'status_text', 'vacation_total', 'vacation_used', 'vacation_days_per_year',
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
    




class TeamMemberDetailSerializer(TeamMemberSummarySerializer):
    vacation_days_per_year = serializers.FloatField(required=False)
    joined_at = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = Employee
        fields = TeamMemberSummarySerializer.Meta.fields + ['work_days_schema', 'is_active', 'vacation_days_per_year']
        read_only_fields = ['id', 'name', 'first_name', 'last_name', 'initials', 'avatar', 'status_text']

    def update(self, instance, validated_data):
        # Wir fangen vacation_days_per_year ab, damit das super().update() es nicht doppelt verarbeitet
        # bzw. wir kontrollieren, was in der DB landet.
        vacation_days = validated_data.get('vacation_days_per_year')
        
        instance = super().update(instance, validated_data)
        
        # Quota für das aktuelle Kalenderjahr synchronisieren
        current_year = timezone.now().year
        
        # Wenn der Supervisor einen Wert geschickt hat, nehmen wir den direkt!
        # Ansonsten nutzen wir das, was im Employee-Model hinterlegt ist.
        if vacation_days is not None:
            allocated_days = vacation_days
        else:
            allocated_days = VacationService.get_total_days_for_year(instance, current_year)
        
        VacationQuota.objects.update_or_create(
            employee=instance,
            year=current_year,
            defaults={'total_days': allocated_days}
        )
        return instance
    


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
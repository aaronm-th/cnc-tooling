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
    
    vacation_total = serializers.SerializerMethodField()
    vacation_used = serializers.SerializerMethodField()

    ist_hours = serializers.SerializerMethodField()
    soll_hours = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'username', 'first_name', 'last_name', 'email', 'initials',
            'avatar', 'status_text', 'vacation_total', 'vacation_used', 'vacation_days_per_year',
            'weekly_hours', 'joined_at', 'ist_hours', 'soll_hours'
        ]

    def get_ist_hours(self, obj):
        today = timezone.localdate()
        
        # Holt alle Arbeitstage des aktuellen Monats über den korrekten related_name "workdays"
        workdays = obj.workdays.filter(
            date__year=today.year,
            date__month=today.month
        )
        
        # Summiert die total_hours aller Tage dieses Monats
        total_hours = sum(wd.total_hours for wd in workdays)
        return round(float(total_hours), 2)

    def get_soll_hours(self, obj):
        today = timezone.localdate()
        return round(float(obj.get_expected_hours_for_month(year=today.year, month=today.month)), 2)

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.get_photo_url() if hasattr(obj, 'get_photo_url') else None

    def get_status_text(self, obj):
        return "Anwesend" if obj.status else "Abwesend"


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
    work_days_schema = serializers.JSONField(required=False)
    schema_valid_from = serializers.DateField(
        required=False, write_only=True,
        help_text="Ab wann gilt das neue Schema? Default: heute."
    )

    upcoming_schema_change = serializers.SerializerMethodField()
    chip_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def get_upcoming_schema_change(self, obj):
        today = timezone.now().date()
        current_schema = obj.get_schema_for_date(today)
        future = obj.time_histories.filter(valid_from__gt=today).order_by('valid_from').first()

        if not future:
            return None

        if Employee.normalize_schema(future.work_days_schema) == Employee.normalize_schema(current_schema):
            return None

        return {
            'valid_from': future.valid_from.isoformat(),
            'work_days_schema': future.work_days_schema,
    }

    def validate_schema_valid_from(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError(
                "Das Schema kann nicht rückwirkend geändert werden."
            )
        return value

    class Meta:
        model = Employee
        fields = TeamMemberSummarySerializer.Meta.fields + [
            'work_days_schema', 'is_active', 'vacation_days_per_year', 'schema_valid_from', 'upcoming_schema_change', 'chip_id'
        ]
        read_only_fields = ['id', 'name', 'first_name', 'last_name', 'initials', 'avatar', 'status_text']

    def validate_chip_id(self, value):
        if value:
            # Säubern (Leerzeichen weg, Großbuchstaben)
            value = value.strip().upper()
            
            # Prüfen, ob ein ANDERER aktiver Mitarbeiter diesen Chip hat
            queryset = Employee.objects.filter(chip_id=value, is_active=True)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
                
            if queryset.exists():
                # Dieser String-Key triggert im Frontend das Feld 'already_assigned'
                raise serializers.ValidationError("already_assigned")
        return value

    def update(self, instance, validated_data):
            from datetime import timedelta

            # --- RFID CHIP SPEICHERUNG KORREKTUR ---
            # Wir setzen den bereinigten Wert direkt auf die Instanz, BEVOR die restlichen Daten 
            # via super().update verarbeitet und schlussendlich gespeichert werden.
            if 'chip_id' in validated_data:
                chip_val = validated_data.get('chip_id')
                instance.chip_id = chip_val.strip().upper() if chip_val else None

            vacation_days = validated_data.get('vacation_days_per_year')
            new_schema = validated_data.pop('work_days_schema', None)
            valid_from = validated_data.pop('schema_valid_from', None) or timezone.now().date()

            # Führt das Standard-Update inklusive eines .save() durch
            instance = super().update(instance, validated_data)

            if new_schema is not None:
                from core.models import WorkingTimeHistory

                normalized_new = Employee.normalize_schema(new_schema)
                day_before = valid_from - timedelta(days=1)
                preceding_schema = instance.get_schema_for_date(day_before)
                normalized_preceding = Employee.normalize_schema(preceding_schema)

                if normalized_new == normalized_preceding:
                    WorkingTimeHistory.objects.filter(
                        employee=instance, valid_from=valid_from
                    ).delete()
                else:
                    WorkingTimeHistory.objects.update_or_create(
                        employee=instance,
                        valid_from=valid_from,
                        defaults={'work_days_schema': {str(k): v for k, v in new_schema.items()}}
                    )

            current_year = timezone.now().year
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
    chip_id = serializers.CharField(required=False, allow_null=True, allow_blank=True) # <-- NEU

    def validate(self, attrs):
        """
        Objektübergreifende Validierung: Verhindert, dass ein Mitarbeiter 
        mit exakt demselben Vor- und Nachnamen doppelt angelegt wird.
        """
        first_name = attrs.get('first_name')
        last_name = attrs.get('last_name')
        chip_id = attrs.get('chip_id')

        # Falls wir im "Edit"-Modus sind, müssen wir die ID ignorieren (falls vorhanden im Kontext)
        # Für reine Create-Views reicht dieser einfache Check:
        if Employee.objects.filter(first_name=first_name, last_name=last_name, is_active=True).exists():
            raise serializers.ValidationError({
                "last_name": "Ein aktiver Mitarbeiter mit diesem Vor- und Nachnamen existiert bereits."
            })
        
        if chip_id:
            chip_id = chip_id.strip().upper()
            attrs['chip_id'] = chip_id
            conflict_emp = Employee.objects.filter(chip_id=chip_id, is_active=True).first()
            if conflict_emp:
                # Wir werfen ein strukturiertes JSON ab, das der Store / Frontend versteht
                raise serializers.ValidationError({
                    "status": "already_assigned",
                    "assigned_to": conflict_emp.get_full_name()
                })
            
        return attrs

    def validate_work_days_schema(self, value):
        if isinstance(value, dict):
            return {str(k): v for k, v in value.items()}
        return value
    

class MonthProcessSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    employee_id = serializers.IntegerField(required=False)

    def validate_employee_id(self, value):
        if not Employee.objects.filter(id=value).exists():
            raise serializers.ValidationError("Mitarbeiter existiert nicht.")
        return value
from rest_framework import serializers
from django.utils import timezone
import pytz 
from decimal import Decimal
from .models import Employee, VacationQuota, Notification
from .services.vacation_service import VacationService  # Import deines zentralen Services
from drf_spectacular.utils import extend_schema_field
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer



# 1. Einfache Hilfs-Serializer
class SimpleResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Generiert standardmäßig {"refresh": "...", "access": "..."}
        data = super().validate(attrs)
        
        # Erweitert das Standard-Dictionary flach auf der obersten Ebene
        data['success'] = True
        data['user'] = EmployeeSerializer(self.user, context=self.context).data
        
        return data


# 2. Modell-Serializer
class EmployeeSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    name = serializers.ReadOnlyField() 
    username = serializers.ReadOnlyField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    initials = serializers.ReadOnlyField()
    status_text = serializers.SerializerMethodField()
    is_supervisor = serializers.SerializerMethodField()

    email = serializers.CharField(
        allow_blank=True, 
        allow_null=True, 
        required=False,
        validators=[]
    )

    class Meta:
        model = Employee
        fields = [
            'id', 'first_name', 'last_name', 'name', 'initials', 
            'email', 'phone', 'status_text', 'avatar', 'is_supervisor', 'username', 'password'
        ]
        read_only_fields = ['id']

    def update(self, instance, validated_data):
        # 1. Passwort-Handling
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        # 2. Foto-Handling (Ausgelagert aus der View)
        request = self.context.get('request')
        if request and 'photo' in request.data:
            photo_data = request.data.get('photo')
            if photo_data == '': # Vue will löschen
                if instance.photo:
                    instance.photo.delete(save=False)
                instance.photo = None
        elif request and 'photo' in request.FILES: # Neues Foto
            if instance.photo:
                instance.photo.delete(save=False)
            instance.photo = request.FILES['photo']

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if ret.get('email') in [None, 'null', '']:
            ret['email'] = ''
        return ret
    

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return None

    @extend_schema_field(serializers.CharField())
    def get_status_text(self, obj):
        return "Anwesend" if obj.status else "Abwesend"
    
    @extend_schema_field(serializers.BooleanField())
    def get_is_supervisor(self, obj):
        return obj.is_superuser if hasattr(obj, 'is_superuser') else False


class VacationQuotaSerializer(serializers.ModelSerializer):
    total_available_days = serializers.FloatField(read_only=True)
    used_days = serializers.SerializerMethodField()
    total_days = serializers.FloatField()
    carried_over = serializers.FloatField()

    class Meta:
        model = VacationQuota
        fields = [
            'year', 'total_days', 'carried_over', 
            'total_available_days', 
            'used_days'
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_used_days(self, obj):
        # Berechne die Anzahl der bereits genutzten Urlaubstage
        return VacationService.get_used_days(obj.employee, obj.year)

        

class NotificationSerializer(serializers.ModelSerializer):
    type = serializers.ReadOnlyField(source='notification_type')
    time = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'type', 'read', 'time', 'link_to']

    @extend_schema_field(serializers.CharField())
    def get_time(self, obj):
        now = timezone.now()
        diff = now - obj.created_at
        if diff < timezone.timedelta(minutes=1):
            return "Gerade eben"
        local_tz = pytz.timezone("Europe/Berlin")
        local_time = obj.created_at.astimezone(local_tz)
        return local_time.strftime("%d.%m.%Y %H:%M")


# 3. Zusammengesetzte Serializer
class UserLoginResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = EmployeeSerializer()



class ScratchpadSerializer(serializers.Serializer):
    notes = serializers.CharField(allow_blank=True)


class OvertimeInfoSerializer(serializers.Serializer):
    balance = serializers.FloatField()
    weekly_hours = serializers.FloatField()


class UserStatsSerializer(serializers.Serializer):
    vacation = serializers.SerializerMethodField()
    overtime = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    joined_at = serializers.SerializerMethodField()
    is_supervisor = serializers.SerializerMethodField()
    username = serializers.ReadOnlyField()

    @extend_schema_field(VacationQuotaSerializer)
    def get_vacation(self, obj):
        current_year = timezone.now().year
        
        # Wir Suchen NUR noch nach der bestehenden Quote in der Datenbank
        quota = VacationQuota.objects.filter(employee=obj, year=current_year).first()
        
        if not quota:
            # Fallback, falls für das Jahr (noch) keine Quote existiert
            return {
                "year": current_year,
                "total_days": float(obj.vacation_days_per_year),
                "carried_over": 0.0,
                "remaining_days": float(obj.vacation_days_per_year),
                "total_available_days": float(obj.vacation_days_per_year),
                "used_days": 0
            }
            
        return VacationQuotaSerializer(quota, context=self.context).data

    @extend_schema_field(OvertimeInfoSerializer)
    def get_overtime(self, obj):
        return {
            "balance": float(obj.overtime_balance)
    }

    @extend_schema_field(serializers.CharField())
    def get_status(self, obj):
        return "Anwesend" if obj.status else "Abwesend"

    @extend_schema_field(serializers.CharField())
    def get_joined_at(self, obj):
        # Gibt das ISO-Format zurück (besser für das Frontend zum Parsen) oder formatiert
        return obj.joined_at.strftime("%Y-%m-%d") if obj.joined_at else None
    
    @extend_schema_field(serializers.BooleanField())
    def get_is_supervisor(self, obj):
        return obj.is_superuser if hasattr(obj, 'is_superuser') else False
    
    @extend_schema_field(serializers.CharField())
    def get_username(self, obj):
        return obj.username
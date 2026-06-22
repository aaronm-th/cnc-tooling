from rest_framework import serializers
from core.models import Employee

class TerminalUserSerializer(serializers.ModelSerializer):
    # SerializerMethodField für die Logik (Anwesend/Abwesend)
    status = serializers.SerializerMethodField()
    # ImageField wandelt das Foto automatisch in eine absolute URL um
    avatar = serializers.ImageField(source='photo', read_only=True)
    # Falls 'name' eine Property in deinem Model ist
    name = serializers.ReadOnlyField()

    class Meta:
        model = Employee
        fields = ['id', 'name', 'initials', 'status', 'avatar']

    def get_status(self, obj):
        # Nutzt dein vorhandenes 'status'-Attribut/Property vom Employee-Model
        return "Anwesend" if obj.status else "Abwesend"
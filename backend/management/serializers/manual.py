import datetime
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from core.models import Employee, is_month_locked
from attendance.models import WorkDay, WorkSession

class ManualSessionSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    check_in = serializers.TimeField()
    check_out = serializers.TimeField()

    def validate(self, attrs):
        if attrs['check_in'] >= attrs['check_out']:
            raise serializers.ValidationError(_("Die Gehen-Zeit muss nach der Kommen-Zeit liegen."))
        return attrs


class ManualEntrySerializer(serializers.Serializer):
    ENTRY_TYPES = (('vacation', 'Urlaub'), ('sick', 'Krankheit'), ('work', 'Zeiterfassung'))

    member_id = serializers.IntegerField(write_only=True)
    type = serializers.ChoiceField(choices=ENTRY_TYPES)
    date = serializers.DateField()
    note = serializers.CharField(style={'base_template': 'textarea.html'})
    hours_or_days = serializers.FloatField(required=False, min_value=0.0)
    sessions = ManualSessionSerializer(many=True, required=False)
    deleted_session_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

    def validate(self, attrs):
        entry_type = attrs.get('type')
        date_obj = attrs.get('date')
        
        employee = get_object_or_404(Employee, id=attrs.get('member_id'))
        self.context['employee_instance'] = employee

        if employee.joined_at and date_obj < employee.joined_at:
            joined_formatted = employee.joined_at.strftime('%d.%m.%Y')
            raise serializers.ValidationError({
                "date": _(f"Einträge vor dem Eintrittsdatum ({joined_formatted}) sind nicht erlaubt.")
            })

        # NEU: Monatssperre – verhindert neue/geänderte manuelle Einträge für
        # bereits abgeschlossene (per closeEmployeeMonth) Monate.
        if is_month_locked(employee, date_obj):
            month_formatted = date_obj.strftime('%m/%Y')
            raise serializers.ValidationError({
                "date": _(f"Der Monat {month_formatted} ist bereits abgeschlossen und kann nicht mehr bearbeitet werden.")
            })

        if entry_type in ['vacation', 'sick']:
            attrs['sessions'] = []
        elif entry_type == 'work':
            sessions = attrs.get('sessions') or []
            if not sessions:
                raise serializers.ValidationError({"sessions": _("Mindestens eine Kommen-/Gehen-Zeit ist erforderlich.")})

            ordered = sorted(sessions, key=lambda s: s['check_in'])
            for prev, nxt in zip(ordered, ordered[1:]):
                if prev['check_out'] > nxt['check_in']:
                    raise serializers.ValidationError({"sessions": _("Die eingegebenen Zeiten überschneiden sich.")})
            attrs['hours_or_days'] = None

        return attrs

    def create(self, validated_data):
        employee = self.context['employee_instance']
        entry_type = validated_data['type']
        date_obj = validated_data['date']
        note = validated_data['note']
        supervisor = self.context['request'].user

        work_day, created = WorkDay.objects.get_or_create(
            employee=employee, 
            date=date_obj,
            defaults={'day_type': entry_type, 'note': f"Bemerkung von {supervisor.get_full_name() or supervisor.username}: {note}"}
        )
        
        if not created:
            work_day.day_type = entry_type
            work_day.note = f"Bemerkung von {supervisor.get_full_name() or supervisor.username}: {note}"
            work_day.save()

        current_tz = timezone.get_current_timezone()

        if entry_type == 'work':
            deleted_ids = validated_data.get('deleted_session_ids', [])
            if deleted_ids:
                work_day.sessions.filter(id__in=deleted_ids).delete()

            for s in validated_data.get('sessions', []):
                naive_check_in = datetime.datetime.combine(date_obj, s['check_in'])
                naive_check_out = datetime.datetime.combine(date_obj, s['check_out'])
                aware_check_in = timezone.make_aware(naive_check_in, current_tz)
                aware_check_out = timezone.make_aware(naive_check_out, current_tz)

                session = work_day.sessions.filter(id=s['id']).first() if s.get('id') else None

                if session:
                    session.check_in = aware_check_in
                    session.check_out = aware_check_out

                    if hasattr(session, 'is_auto_checkout'):
                        session.is_auto_checkout = False

                    session.save()
                else:
                    WorkSession.objects.create(work_day=work_day, check_in=aware_check_in, check_out=aware_check_out)
        else:
            work_day.sessions.all().delete()

        return validated_data

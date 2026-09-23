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
    
    # Unterstützt Einzeltag ODER Datumsspanne
    date = serializers.DateField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)

    note = serializers.CharField(style={'base_template': 'textarea.html'})
    hours_or_days = serializers.FloatField(required=False, min_value=0.0)
    sessions = ManualSessionSerializer(many=True, required=False)
    deleted_session_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)

    def validate(self, attrs):
        entry_type = attrs.get('type')
        
        # 1. Datumsbereich auflösen
        if entry_type in ['vacation', 'sick']:
            start = attrs.get('start_date') or attrs.get('date')
            end = attrs.get('end_date') or start

            if not start or not end:
                raise serializers.ValidationError({"start_date": _("Start- und Enddatum müssen angegeben werden.")})

            if start > end:
                raise serializers.ValidationError({"end_date": _("Das Enddatum muss nach oder auf dem Startdatum liegen.")})

            attrs['start_date'] = start
            attrs['end_date'] = end
            attrs['date'] = start  # Hauptdatum/Fallback
        else:
            date_obj = attrs.get('date')
            if not date_obj:
                raise serializers.ValidationError({"date": _("Ein Datum muss angegeben werden.")})
            attrs['start_date'] = date_obj
            attrs['end_date'] = date_obj

        # 2. Mitarbeiter laden
        employee = get_object_or_404(Employee, id=attrs.get('member_id'))
        self.context['employee_instance'] = employee

        # 3. Alle Tage in der Spanne validieren (Eintrittsdatum + Monatssperre)
        current = attrs['start_date']
        while current <= attrs['end_date']:
            if employee.joined_at and current < employee.joined_at:
                joined_formatted = employee.joined_at.strftime('%d.%m.%Y')
                raise serializers.ValidationError({
                    "start_date": _(f"Einträge vor dem Eintrittsdatum ({joined_formatted}) sind nicht erlaubt.")
                })

            if is_month_locked(employee, current):
                month_formatted = current.strftime('%m/%Y')
                raise serializers.ValidationError({
                    "date": _(f"Der Monat {month_formatted} ist bereits abgeschlossen und kann nicht mehr bearbeitet werden.")
                })
            current += datetime.timedelta(days=1)

        # 4. Typ-spezifische Prüfungen
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
        start_date = validated_data['start_date']
        end_date = validated_data['end_date']
        note = validated_data['note']
        supervisor = self.context['request'].user
        current_tz = timezone.get_current_timezone()

        # Über alle Tage in der Spanne iterieren
        current = start_date
        while current <= end_date:
            work_day, created = WorkDay.objects.get_or_create(
                employee=employee, 
                date=current,
                defaults={
                    'day_type': entry_type, 
                    'note': f"Bemerkung von {supervisor.get_full_name() or supervisor.username}: {note}"
                }
            )
            
            if not created:
                work_day.day_type = entry_type
                work_day.note = f"Bemerkung von {supervisor.get_full_name() or supervisor.username}: {note}"
                work_day.save()

            if entry_type == 'work':
                deleted_ids = validated_data.get('deleted_session_ids', [])
                if deleted_ids:
                    work_day.sessions.filter(id__in=deleted_ids).delete()

                for s in validated_data.get('sessions', []):
                    naive_check_in = datetime.datetime.combine(current, s['check_in'])
                    naive_check_out = datetime.datetime.combine(current, s['check_out'])
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
                # Bei Urlaub / Krankheit bestehende Sessions an dem Tag löschen
                work_day.sessions.all().delete()

            current += datetime.timedelta(days=1)

        return validated_data
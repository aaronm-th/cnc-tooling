from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated

from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView

from attendance.models import LeaveRequest, WSChangeRequest, WorkDay
from management.permissions import IsSupervisor
from management.serializers import TeamMemberSummarySerializer, TeamMemberDetailSerializer, CreateEditEmployeeSerializer, MonthProcessSerializer
from core.models import Employee, VacationQuota, MonthlyPayout

from decimal import Decimal


class SupervisorDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated, IsSupervisor]

    def get(self, request):
        today = timezone.now().date()
        subordinates = Employee.objects.filter(is_active=True, is_superuser=False)
        
        on_leave_today = WorkDay.objects.filter(
            employee__in=subordinates, date=today, day_type__in=['vacation', 'sick']
        ).count()

        leave_requests = LeaveRequest.objects.filter(
            employee__is_superuser=False, status='pending'
            ).select_related('employee').count()

        change_requests = WSChangeRequest.objects.filter(
            requested_by__is_superuser=False, status='pending'
            ).select_related('employee').count()

        employees = Employee.objects.filter(is_superuser=False, is_active=True)
        active_employees = sum(1 for emp in employees if emp.status == True)


        # REFACTOR: Nutzt den neuen Serializer für die einheitliche, fehlerfreie Karten-Anzeige
        serializer = TeamMemberSummarySerializer(subordinates, many=True, context={'request': request})

        return Response({
            "employees": serializer.data,
            "employees_count": subordinates.count(),
            "on_leave_today": on_leave_today,
            "active_employees": active_employees
        })
    

class TeamMemberListView(ListAPIView):
    permission_classes = [IsAuthenticated, IsSupervisor]
    serializer_class = TeamMemberSummarySerializer

    def get_queryset(self):
        return Employee.objects.filter(is_superuser=False, is_active=True).order_by('last_name')
    

class TeamMemberDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET, PUT, PATCH, DELETE /mgmt/team/<int:pk>/
    Zeigt Details, editiert Stammdaten via Serializer oder setzt den Mitarbeiter inaktiv.
    """
    permission_classes = [IsAuthenticated, IsSupervisor]
    serializer_class = TeamMemberDetailSerializer # Garantiert korrekte Feldzuordnung
    
    def get_queryset(self):
        return Employee.objects.filter(is_superuser=False, is_active=True).order_by('last_name')


    def patch(self, request, *args, **kwargs):

        try:
            return super().patch(request, *args, **kwargs)
        except DRFValidationError as e:
            if 'chip_id' in e.detail and 'already_assigned' in e.detail['chip_id']:
                raw_chip = request.data.get('chip_id', '').strip().upper()
                conflict_emp = Employee.objects.filter(chip_id=raw_chip, is_active=True).first()
                return Response({
                    "status": "already_assigned",
                    "assigned_to": conflict_emp.get_full_name() if conflict_emp else "Ein anderer Mitarbeiter"
                }, status=status.HTTP_200_OK)
            raise e
        
    def perform_update(self, serializer):
        with transaction.atomic():
            instance = serializer.save()

            if instance.chip_id:
                cache.delete('latest_unregistered_rfid')

    def perform_destroy(self, instance):
        # Soft-Delete: Mitarbeiter wird nur inaktiv gesetzt
        instance.is_active = False
        instance.save()


class TeamCalendarEventsView(APIView):
    permission_classes = [IsAuthenticated, IsSupervisor]

    def get(self, request):
        subordinates = Employee.objects.filter(is_superuser=False, is_active=True)

        calendar_days = WorkDay.objects.filter(
            employee__in=subordinates,
        ).exclude(
            day_type='holiday'
        ).exclude(
            day_type='weekend', sessions__isnull=True
        ).select_related('employee').prefetch_related('sessions').distinct()

        events_data = []

        # 1. Echte Arbeitszeiten & manuelle Einträge (z.B. 'work', 'sick')
        for day in calendar_days:
            day_sessions = sorted(day.sessions.all(), key=lambda s: s.check_in)
            
            session_strings = []
            for session in day_sessions:
                in_time = session.check_in.astimezone().strftime("%H:%M")
                if session.check_out:
                    out_time = session.check_out.astimezone().strftime("%H:%M")
                    session_strings.append(f"{in_time} - {out_time}")
                else:
                    session_strings.append(f"{in_time} - (offen)")

            if session_strings:
                if day.note:
                    session_strings.append(f"{day.note}")
                session_strings.append(f"TOTAL:Gesamtzeit: {day.total_hours} Std.")
                time_note = "|".join(session_strings)
            else:
                # Wichtig: Wenn keine Notiz existiert, None setzen (wird im JSON zu null)
                time_note = day.note if day.note else None

            events_data.append({
                "id": f"wd-{day.id}",
                "userName": day.employee.get_full_name(),
                "date": day.date.isoformat(),
                "type": day.day_type,
                "title": day.get_day_type_display(),
                "note": time_note  # Reicht null weiter, Tooltip blendet sich aus
            })

        # 2. Ausstehende Urlaubsanträge
        pending_leaves = LeaveRequest.objects.filter(
            employee__is_superuser=False, status='pending'
        ).select_related('employee')

        for leave in pending_leaves:
            curr_date = leave.leave_start
            while curr_date <= leave.leave_end:
                events_data.append({
                    "id": f"lr-{leave.id}-{curr_date.isoformat()}",
                    "userName": leave.employee.get_full_name(),
                    "date": curr_date.isoformat(),
                    "type": "pending",
                    "title": "Abwesenheitsantrag",
                    "note": leave.note if leave.note else None
                })
                curr_date += timedelta(days=1)

        return Response(events_data, status=status.HTTP_200_OK)
    

class CreateEditEmployeeView(APIView):
    permission_classes = [IsSupervisor]

    def post(self, request):
        # Abfangen von RFID-Doppelbelegungen bei Neuanlage
        try:
            serializer = CreateEditEmployeeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
        except DRFValidationError as e:
            if 'non_field_errors' in e.detail and isinstance(e.detail['non_field_errors'], list):
                err_detail = e.detail['non_field_errors'][0]
                if isinstance(err_detail, dict) and err_detail.get('status') == 'already_assigned':
                    return Response(err_detail, status=status.HTTP_200_OK)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        with transaction.atomic():
            try:
                # 1. Mitarbeiter in der DB anlegen (inkl. chip_id)
                user = Employee.objects.create(
                    first_name=validated_data['first_name'],
                    last_name=validated_data['last_name'],
                    vacation_days_per_year=validated_data['vacation_days_per_year'],
                    is_active=True,
                    is_superuser=False,
                    joined_at=validated_data['joined_at'],
                    chip_id=validated_data.get('chip_id') or None  # <-- NEU
                )
                user.refresh_from_db()

                from core.models import WorkingTimeHistory
                WorkingTimeHistory.objects.create(
                    employee=user,
                    valid_from=user.joined_at,
                    work_days_schema=validated_data['work_days_schema'],
                )
                
                # 2. Das offizielle Urlaubskontingent zuteilen
                if user.joined_at:
                    target_year = user.joined_at.year
                    from core.services.vacation_service import VacationService
                    allocated_days = VacationService.get_total_days_for_year(user, target_year)
                    
                    VacationQuota.objects.update_or_create(
                        employee=user, 
                        year=target_year, 
                        defaults={
                            'total_days': Decimal(str(allocated_days)),
                            'carried_over': Decimal('0.0')
                        }
                    )

            except Exception as db_err:
                return Response(
                    {"error": f"Fehler beim Erstellen des Mitarbeiters: {str(db_err)}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Nach erfolgreichem Anlegen den Cache säubern
        if validated_data.get('chip_id'):
            cache.delete('latest_unregistered_rfid')

        return Response({
            "status": "success",
            "success": "Mitarbeiter erfolgreich angelegt.",
            "credentials": {
                "username": user.username,
                "initial_password": user.username
            }
        }, status=status.HTTP_201_CREATED)
    

class PendingChipView(APIView):
    """
    GET /api/mgmt/pending-chip/
    Gibt den letzten, vom ESP32 registrierten, aber unbekannten Chip-Scan aus.
    Benutzt Djangos Standard-Cache (z.B. Redis, Memcached oder Database Cache).
    """
    permission_classes = [IsAuthenticated, IsSupervisor]

    def get(self, request):
        
        # Holt die ID aus dem Cache
        pending_chip = cache.get('latest_unregistered_rfid')
        
        if pending_chip:
            return Response({"chip_id": pending_chip}, status=status.HTTP_200_OK)
        
        return Response({"chip_id": None}, status=status.HTTP_200_OK)


class CloseMonthGlobalView(APIView):
    """
    Sperrt den gewählten Monat global für ALLE aktiven Mitarbeiter (keine Superuser),
    berechnet deren finale Stunden und speichert diese im MonthlyPayout ab.
    """
    permission_classes = [IsSupervisor]

    def post(self, request):
        serializer = MonthProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        year = serializer.validated_data['year']
        month = serializer.validated_data['month']
        
        # Zeitschranke: Man kann den aktuellen Monat nicht vorab schließen
        today = timezone.localdate()
        if year >= today.year and month >= today.month:
            return Response(
                {"detail": "Nur vergangene Monate können global abgeschlossen werden."},
                status=status.HTTP_400_BAD_REQUEST
            )

        employees = Employee.objects.filter(is_active=True, is_superuser=False)
        
        for emp in employees:
            stats = emp.get_hours_balance_for_month(year, month)
            overtime = max(0.0, stats["balance"])
            
            MonthlyPayout.objects.update_or_create(
                employee=emp, year=year, month=month,
                defaults={
                    "worked_hours": stats["worked"],
                    "expected_hours": stats["expected"],
                    "overtime_calculated": overtime,
                    "overtime_paid": overtime,  # Standardmäßig 1:1, vom Chef editierbar
                    "is_processed": True,
                    "processed_at": timezone.now()
                }
            )
            
        return Response(
            {"detail": f"Monat {month}/{year} erfolgreich für alle Mitarbeiter abgerechnet."},
            status=status.HTTP_200_OK
        )


class CloseEmployeeMonthView(APIView):
    """
    Schließt den Monat für einen spezifischen Mitarbeiter ab.
    """
    permission_classes = [IsSupervisor]

    def post(self, request):
        # Hier ist employee_id ein Pflichtfeld
        serializer = MonthProcessSerializer(data=request.data)
        if 'employee_id' not in request.data:
            return Response({"employee_id": ["Dieses Feld ist erforderlich."]}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer.is_valid(raise_exception=True)
        
        year = serializer.validated_data['year']
        month = serializer.validated_data['month']
        emp_id = serializer.validated_data['employee_id']
        
        emp = Employee.objects.get(id=emp_id)
        stats = emp.get_hours_balance_for_month(year, month)
        overtime = max(0.0, stats["balance"])
        
        MonthlyPayout.objects.update_or_create(
            employee=emp, year=year, month=month,
            defaults={
                "worked_hours": stats["worked"],
                "expected_hours": stats["expected"],
                "overtime_calculated": overtime,
                "overtime_paid": overtime,
                "is_processed": True,
                "processed_at": timezone.now()
            }
        )
        
        return Response({"detail": f"Monat für {emp.name} erfolgreich abgerechnet."}, status=status.HTTP_200_OK)


class ReopenEmployeeMonthView(APIView):
    """
    Hebt die Sperre (Auszahlungsfixierung) für einen Mitarbeiter auf,
    indem der MonthlyPayout-Eintrag gelöscht wird.
    """
    permission_classes = [IsSupervisor]

    def post(self, request):
        serializer = MonthProcessSerializer(data=request.data)
        if 'employee_id' not in request.data:
            return Response({"employee_id": ["Dieses Feld ist erforderlich."]}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer.is_valid(raise_exception=True)
        
        year = serializer.validated_data['year']
        month = serializer.validated_data['month']
        emp_id = serializer.validated_data['employee_id']
        
        # Durch das Löschen des Eintrags greifen die Modell-Validierungen nicht mehr 
        # und der Monat ist sofort wieder editierbar (Live-Modus).
        deleted_count, _ = MonthlyPayout.objects.filter(
            employee_id=emp_id, year=year, month=month
        ).delete()
        
        if deleted_count == 0:
            return Response({"detail": "Es existierte kein aktiver Abschluss für diesen Zeitraum."}, status=status.HTTP_404_NOT_FOUND)
            
        return Response({"detail": "Monat wurde für Korrekturen erfolgreich wieder geöffnet."}, status=status.HTTP_200_OK)
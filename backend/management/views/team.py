from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView

from attendance.models import LeaveRequest, WSChangeRequest, WorkDay
from management.permissions import IsSupervisor
from management.serializers import TeamMemberSummarySerializer, TeamMemberDetailSerializer, CreateEditEmployeeSerializer
from core.models import Employee

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
            "requests_count": leave_requests+change_requests,
            "change_requests_count": change_requests,
            "leave_requests_count": leave_requests,
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

    def perform_update(self, serializer):
        # Wir verpacken das Update im Serializer zusätzlich in eine atomare Transaktion,
        # um die Datenbank-Integrität zu sichern.
        with transaction.atomic():
            serializer.save()

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
            day_type__isnull=False
        ).exclude(
            day_type__in=['weekend', 'holiday'] # Ersetze die Strings mit deinen exakten Choice-Keys
        ).select_related('employee').prefetch_related('sessions')

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
        serializer = CreateEditEmployeeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        with transaction.atomic():
            try:
                # 1. Mitarbeiter in der DB anlegen
                user = Employee.objects.create(
                    first_name=validated_data['first_name'],
                    last_name=validated_data['last_name'],
                    work_days_schema=validated_data['work_days_schema'],
                    vacation_days_per_year=validated_data['vacation_days_per_year'],
                    is_active=True,
                    is_superuser=False,
                    joined_at=validated_data['joined_at'],
                )
                
                # Holt das Objekt frisch inklusive dem vom Model generierten Usernamen/Passwort-Hash
                user.refresh_from_db()
                
                # 2. Das offizielle Urlaubskontingent zuteilen
                if user.joined_at:
                    target_year = user.joined_at.year
                    
                    from core.services.vacation_service import VacationService

                    # Nutzen der existierenden Methode aus dem schlanken Service
                    allocated_days = VacationService.get_total_days_for_year(user, target_year)
                    
                    # Quota erstellen oder updaten
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

        return Response({
            "success": "Mitarbeiter erfolgreich angelegt.",
            "credentials": {
                "username": user.username,
                "initial_password": user.username
            }
        }, status=status.HTTP_201_CREATED)
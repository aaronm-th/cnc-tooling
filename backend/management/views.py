from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from core.models import Employee, VacationQuota
from core.services.vacation_service import VacationService
from attendance.models import WorkDay, LeaveRequest, WSChangeRequest
from .permissions import IsSupervisor

# Imports der überarbeiteten Serializer
from .serializers import (
    LeaveRequestSerializer, 
    ChangeRequestSerializer, 
    TeamMemberSummarySerializer,
    TeamMemberDetailSerializer
)
from core.utils import create_notification


class SupervisorDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated, IsSupervisor]

    def get(self, request):
        today = timezone.now().date()
        subordinates = Employee.objects.filter(supervisor=request.user)
        
        on_leave_today = WorkDay.objects.filter(
            employee__in=subordinates, date=today, day_type__in=['vacation', 'sick']
        ).count()

        pending_requests = LeaveRequest.objects.filter(
            employee__supervisor=request.user, status='pending'
        ).select_related('employee')

        active_employees = Employee.objects.filter(supervisor=request.user, status=True).count()

        # REFACTOR: Nutzt den neuen Serializer für die einheitliche, fehlerfreie Karten-Anzeige
        serializer = TeamMemberSummarySerializer(subordinates, many=True, context={'request': request})

        return Response({
            "employees": serializer.data,
            "employees_count": subordinates.count(),
            "on_leave_today": on_leave_today,
            "requests_count": pending_requests.count(),
            "active_employees": active_employees
        })


class TeamMemberListView(ListAPIView):
    permission_classes = [IsAuthenticated, IsSupervisor]
    serializer_class = TeamMemberSummarySerializer

    def get_queryset(self):
        return Employee.objects.filter(supervisor=self.request.user, is_active=True).order_by('last_name')


class TeamMemberDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET, PUT, PATCH, DELETE /mgmt/team/<int:pk>/
    Zeigt Details, editiert Stammdaten via Serializer oder setzt den Mitarbeiter inaktiv.
    """
    permission_classes = [IsAuthenticated, IsSupervisor]
    serializer_class = TeamMemberDetailSerializer # <-- Garantiert korrekte Feldzuordnung
    
    def get_queryset(self):
        return Employee.objects.filter(supervisor=self.request.user)

    def update(self, request, *args, **kwargs):
        # Nutzt die Standard-DRF Update-Logik, die unseren Serializer triggert
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Das eigentliche Update führen wir gesichert in einer Transaktion aus
        with transaction.atomic():
            self.perform_update(serializer)
            
            # Holt den upgedateten Wert direkt aus den validierten Daten des Frontends
            new_vacation_days = request.data.get('vacation_days_per_year')
            
            if new_vacation_days is not None:
                current_year = timezone.now().year
                # Der Supervisor hat gesprochen: Wir updaten das Quota direkt mit der manuellen Eingabe,
                # anstatt die Pro-Rata-Formel des Services drüberzubügeln!
                VacationQuota.objects.update_or_create(
                    employee=instance,
                    year=current_year,
                    defaults={
                        'total_days': float(new_vacation_days),
                    }
                )

        return Response({
            "message": f"Mitarbeiter {instance.get_full_name()} erfolgreich aktualisiert.",
            "id": instance.id
        }, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class HandleLeaveRequestView(APIView):
    permission_classes = [IsAuthenticated, IsSupervisor]
    serializer_class = LeaveRequestSerializer
    
    def get(self, request):
        leave_requests = LeaveRequest.objects.filter(
            employee__supervisor=request.user
        ).exclude(status='cancelled').select_related('employee').order_by('-request_date')
        
        serializer = LeaveRequestSerializer(leave_requests, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        request_id = request.data.get('request_id')
        action = request.data.get('action')
        
        leave_request = get_object_or_404(LeaveRequest, id=request_id, employee__supervisor=request.user)

        with transaction.atomic():
            if action == 'approve':
                leave_request.status = 'approved'
                curr = leave_request.leave_start
                while curr <= leave_request.leave_end:
                    if curr.weekday() < 5:
                        WorkDay.objects.update_or_create(
                            employee=leave_request.employee,
                            date=curr,
                            note=leave_request.note,
                            defaults={'day_type': leave_request.leave_type}
                        )
                    curr += timedelta(days=1)
                msg = "Antrag genehmigt."
            elif action == 'reject':
                leave_request.status = 'rejected'
                msg = "Antrag abgelehnt."
            else:
                return Response({'error': 'Ungültige Aktion'}, status=status.HTTP_400_BAD_REQUEST)

            leave_request.reviewed_date = timezone.now()
            leave_request.reviewed_by = request.user
            leave_request.save()

            self._notify_employee(leave_request, action)
            return Response({'message': msg, 'status': leave_request.status})

    def _notify_employee(self, leave_request, action):
        status_txt = "genehmigt" if action == 'approve' else "abgelehnt"
        leave_start_str = leave_request.leave_start.strftime('%d.%m.%Y')
        leave_end_str = leave_request.leave_end.strftime('%d.%m.%Y')
        date_str = f"für den {leave_start_str}" if leave_request.leave_start == leave_request.leave_end else f"vom {leave_start_str} - {leave_end_str}"

        create_notification(
            user=leave_request.employee,
            title=f"Urlaubsantrag {status_txt}",
            message=f"Dein Antrag {date_str} wurde {status_txt}.",
            notification_type='success' if action == 'approve' else 'error',
            link_to="requests"
        )


class HandleChangeRequestView(APIView):
    permission_classes = [IsAuthenticated, IsSupervisor]

    def get(self, request):
        change_requests = WSChangeRequest.objects.filter(
            requested_by__supervisor=request.user
        ).exclude(status='cancelled').select_related('requested_by', 'work_day').order_by('-request_date')
        
        serializer = ChangeRequestSerializer(change_requests, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        request_id = request.data.get('request_id')
        action = request.data.get('action')
        
        change_req = get_object_or_404(WSChangeRequest, id=request_id, requested_by__supervisor=request.user)

        if action == 'approve':
            try:
                change_req.approve(reviewer=request.user)
            except ValidationError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        elif action == 'reject':
            reason = request.data.get('admin_note', '')
            change_req.reject(reviewer=request.user, reason=reason)
        
        self._notify_employee(change_req, action)
        return Response({'status': change_req.status})

    def _notify_employee(self, change_req, action):
        status_txt = "genehmigt" if action == 'approve' else "abgelehnt"
        date_str = change_req.work_day.date.strftime('%d.%m.%Y')

        create_notification(
            user=change_req.requested_by,
            title=f"Änderungsantrag {status_txt}",
            message=f"{change_req.reviewed_by} hat deinen Änderungsantrag für den {date_str} {status_txt}.",
            notification_type='success' if action == 'approve' else 'error',
            link_to='requests'
        )


class TeamCalendarEventsView(APIView):
    permission_classes = [IsAuthenticated, IsSupervisor]

    def get(self, request):
        subordinates = Employee.objects.filter(supervisor=request.user, is_active=True)

        calendar_days = WorkDay.objects.filter(
            employee__in=subordinates, day_type__isnull=False
        ).exclude(day_type__in=['work']).select_related('employee')

        events_data = []
        for day in calendar_days:
            events_data.append({
                "id": f"wd-{day.id}",
                "userName": day.employee.get_full_name(),
                "date": day.date.isoformat(),
                "type": day.day_type,
                "title": day.get_day_type_display(),
                "note": day.note if day.note else ""
            })

        pending_leaves = LeaveRequest.objects.filter(
            employee__supervisor=request.user, status='pending', leave_type='vacation'
        ).select_related('employee')

        for leave in pending_leaves:
            curr_date = leave.leave_start
            while curr_date <= leave.leave_end:
                if curr_date.weekday() < 5:
                    events_data.append({
                        "id": f"lr-{leave.id}-{curr_date}",
                        "userName": leave.employee.get_full_name(),
                        "date": curr_date.isoformat(),
                        "type": "pending",
                        "title": f"{leave.get_leave_type_display()} (offen)",
                        "note": leave.note if leave.note else ""
                    })
                curr_date += timedelta(days=1)

        return Response(events_data, status=status.HTTP_200_OK)
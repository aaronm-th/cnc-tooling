from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from attendance.models import LeaveRequest, WSChangeRequest, WorkDay
from management.permissions import IsSupervisor
from management.serializers import LeaveRequestSerializer, ChangeRequestSerializer
from core.models import first_locked_month
from core.utils import create_notification
from django.core.exceptions import ValidationError



class HandleLeaveRequestView(APIView):
    permission_classes = [IsAuthenticated, IsSupervisor]
    serializer_class = LeaveRequestSerializer
    
    def get(self, request):
        leave_requests = LeaveRequest.objects.exclude(status='cancelled').select_related('employee').order_by('-request_date')
        
        serializer = LeaveRequestSerializer(leave_requests, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        request_id = request.data.get('request_id')
        action = request.data.get('action')
        
        leave_request = get_object_or_404(LeaveRequest, id=request_id)

        # NEU: Monatssperre - nur beim Genehmigen relevant. Ablehnen eines
        # Antrags für einen gesperrten Monat bleibt bewusst immer möglich,
        # da es keine Stunden/WorkDays verändert.
        if action == 'approve':
            locked_month = first_locked_month(
                leave_request.employee, leave_request.leave_start, leave_request.leave_end
            )
            if locked_month:
                return Response(
                    {'error': f"Der Monat {locked_month.strftime('%m/%Y')} ist bereits abgeschlossen "
                               "und kann nicht mehr bearbeitet werden."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        with transaction.atomic():
            if action == 'approve':
                leave_request.status = 'approved'

                target_day_type = getattr(leave_request, 'leave_type', 'vacation')

                curr = leave_request.leave_start
                while curr <= leave_request.leave_end:
                    if curr.weekday() < 5:
                        WorkDay.objects.update_or_create(
                            employee=leave_request.employee,
                            date=curr,
                            defaults={
                                'day_type': target_day_type,
                                'note': leave_request.note if leave_request.note else ""
                            }
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
            title=f"Abwesenheitsantrag {status_txt}",
            message=f"Dein Antrag {date_str} wurde {status_txt}.",
            notification_type='success' if action == 'approve' else 'error',
            link_to="requests"
        )



class HandleChangeRequestView(APIView):
    permission_classes = [IsAuthenticated, IsSupervisor]

    def get(self, request):
        change_requests = WSChangeRequest.objects.filter(
            requested_by__is_superuser=False
        ).exclude(status='cancelled').select_related('requested_by', 'work_day').order_by('-request_date')
        
        serializer = ChangeRequestSerializer(change_requests, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        request_id = request.data.get('request_id')
        action = request.data.get('action')
        
        change_req = get_object_or_404(WSChangeRequest, id=request_id)

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

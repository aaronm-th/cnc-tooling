from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from rest_framework.exceptions import ValidationError

from .models import WorkSession, WSChangeRequest, WorkDay, LeaveRequest
from .serializers import (LeaveRequestSerializer, WorkSessionSerializer, 
WorkSessionDetailSerializer, WSChangeRequestSerializer)

from .utils import send_leave_notification, send_change_notification





# --- LEAVE REQUESTS ---

class LeaveRequestListCreateAPIView(ListCreateAPIView):
    """GET: Liste der Anträge, POST: Neuen Antrag erstellen"""
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeaveRequest.objects.filter(employee=self.request.user).order_by('-request_date')

    def perform_create(self, serializer):
        with transaction.atomic():
            leave = serializer.save(employee=self.request.user)
            send_leave_notification(leave)

class LeaveRequestDetailAPIView(RetrieveUpdateDestroyAPIView):
    """PUT: Bearbeiten, DELETE: Stornieren"""
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return LeaveRequest.objects.filter(employee=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != 'pending':
            raise ValidationError({"detail": "Nur offene Anträge können bearbeitet werden."})
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        
        instance = self.get_object()
        
        if instance.status in ['rejected', 'cancelled']:
            raise ValidationError({"detail": "Antrag ist bereits erledigt oder storniert."})
        
        if instance.leave_end < timezone.now().date():
            raise ValidationError({"detail": "Vergangene Anträge können nicht storniert werden."})
        
        with transaction.atomic():
            if instance.status == 'approved':
                WorkDay.objects.filter(
                    employee=request.user, 
                    date__range=[instance.leave_start, instance.leave_end]
                ).exclude(day_type=WorkDay.DayType.WORK).delete()
            
            instance.status = 'cancelled'
            instance.save()
            return Response({"status": "cancelled", "message": "Antrag wurde storniert."}, status=status.HTTP_200_OK)


class ChangeRequestListAPIView(ListCreateAPIView):
    """GET: Liste aller Anträge, POST: Neuen Antrag erstellen"""
    serializer_class = WSChangeRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WSChangeRequest.objects.filter(requested_by=self.request.user).order_by('-request_date')


class WorkSessionRequestAPIView(APIView):
    """
    Korrektur existierender Sessions: Details abrufen, Antrag stellen/aktualisieren, Antrag löschen.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        session = get_object_or_404(WorkSession, id=pk, work_day__employee=request.user)
        return Response(WorkSessionDetailSerializer(session).data)

    def post(self, request, pk):
        session = get_object_or_404(WorkSession, id=pk, work_day__employee=request.user)
        existing_request = session.change_requests.filter(status='pending').first()

        # "Zurückziehen"-Logik: Wenn Zeiten dem Original entsprechen, Antrag löschen
        requested_in = request.data.get('requested_check_in')
        requested_out = request.data.get('requested_check_out')
        
        if existing_request and requested_in and requested_out:
            orig_in = session.check_in.isoformat()
            orig_out = session.check_out.isoformat() if session.check_out else ""
            if requested_in.startswith(orig_in) and requested_out.startswith(orig_out):
                existing_request.delete()
                return Response({"message": "Antrag gelöscht (Zeiten auf Original gesetzt)."}, status=status.HTTP_200_OK)

        serializer = WSChangeRequestSerializer(existing_request, data=request.data, partial=True) if existing_request \
                     else WSChangeRequestSerializer(data=request.data)

        if serializer.is_valid():
            # workday wird automatisch im Model-save() aus der session gezogen, 
            # wir übergeben es hier zur Sicherheit explizit.
            change_request = serializer.save(
                worksession=session, 
                work_day=session.work_day,
                requested_by=request.user, 
                status='pending'
            )
            send_change_notification(change_request)
            return Response(serializer.data, status=status.HTTP_200_OK if existing_request else status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        session = get_object_or_404(WorkSession, id=pk, work_day__employee=request.user)
        existing_request = session.change_requests.filter(status='pending').first()
        if existing_request:
            existing_request.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Kein offener Antrag gefunden."}, status=status.HTTP_404_NOT_FOUND)


class WorkDayRequestAPIView(APIView):
    """
    Manuelle Nachmeldung für leere Tage: Erstellt einen Antrag ohne existierende Session.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        workday = get_object_or_404(WorkDay, id=pk, employee=request.user)
        
        # Bestehenden Neuanlage-Antrag für diesen Tag suchen
        existing_request = WSChangeRequest.objects.filter(
            work_day=workday, 
            worksession__isnull=True, 
            status='pending'
        ).first()

        serializer = WSChangeRequestSerializer(existing_request, data=request.data, partial=True) if existing_request \
                     else WSChangeRequestSerializer(data=request.data)

        if serializer.is_valid():
            change_request = serializer.save(
                work_day=workday,
                worksession=None, 
                requested_by=request.user, 
                status='pending'
            )
            send_change_notification(change_request)
            return Response(serializer.data, status=status.HTTP_200_OK if existing_request else status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkDaySessionsAPIView(APIView):
    """Gibt alle Sessions eines bestimmten Tages zurück (für die Listenansicht im Modal)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        workday = get_object_or_404(WorkDay, id=pk, employee=request.user)
        sessions = workday.sessions.all()
        serializer = WorkSessionDetailSerializer(sessions, many=True)
        return Response({
            "date": workday.date,
            "sessions": serializer.data
        })
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from management.permissions import IsSupervisor
from management.serializers import ManualEntrySerializer

from core.models import Employee, is_month_locked
from attendance.models import WorkDay
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError


class ManualEntriesView(APIView):
    permission_classes = [IsSupervisor]

    def get(self, request, *args, **kwargs):
        """
        Liefert einen ggf. bereits existierenden WorkDay inkl. seiner Sessions
        (mit IDs) zurück, damit das Modal bestehende Stempelzeiten zum
        Bearbeiten vorbefüllen kann, statt sie blind zu überschreiben.

        GET /api/mgmt/manual-entries/?member_id=<id>&date=YYYY-MM-DD
        """
        member_id = request.query_params.get('member_id')
        date_str = request.query_params.get('date')

        if not member_id or not date_str:
            return Response(
                {"error": "member_id und date sind erforderlich."},
                status=status.HTTP_400_BAD_REQUEST
            )

        employee = get_object_or_404(Employee, id=member_id)

        try:
            work_day = WorkDay.objects.prefetch_related('sessions').get(
                employee=employee, date=date_str
            )
        except WorkDay.DoesNotExist:
            return Response({"exists": False, "day_type": None, "sessions": [], "warning": None})

        sessions = [
            {
                "id": s.id,
                "check_in": timezone.localtime(s.check_in).strftime("%H:%M"),
                "check_out": timezone.localtime(s.check_out).strftime("%H:%M") if s.check_out else None,
                "is_auto_checkout": getattr(s, 'is_auto_checkout', False),
            }
            for s in sorted(work_day.sessions.all(), key=lambda s: s.check_in)
        ]

        # --- WARNUNG ERMITTELN ---
        # Passe die Bedingung unten an dein 'WorkDay'- bzw. 'WorkSession'-Modell an:
        warning_msg = None
        
        # Variante A: Auslesen aus einem Eigenschafts-Feld / Property deines Models
        if getattr(work_day, 'has_auto_checkout', False):
            warning_msg = "Automatische Ausstempelung registriert. Bitte Arbeitszeiten überprüfen."
        elif getattr(work_day, 'warning', None):
            warning_msg = work_day.warning

        # Variante B: Prüfung der WorkSessions auf Auto-Checkout / offenes Checkout
        elif any(getattr(s, 'is_auto_checkout', False) for s in work_day.sessions.all()):
            warning_msg = "Auto-Checkout wurde für diesen Tag durchgeführt."
        
        return Response({
            "exists": True,
            "day_type": work_day.day_type,
            "day_type_display": work_day.get_day_type_display(),
            "sessions": sessions,
            "warning": warning_msg,  # <-- NEU: Wird jetzt an das Frontend übergeben
        })


    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = ManualEntrySerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            try:
                serializer.save()
            except DjangoValidationError as exc:
                error_messages = exc.message_dict.get('__all__', [str(exc)])
                raise DRFValidationError({"non_field_errors": error_messages})

            return Response(
                {"detail": "Manueller Eintrag erfolgreich gebucht."},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        """
        Löscht einen kompletten manuellen Eintrag (WorkDay inkl. aller
        zugehörigen WorkSessions per CASCADE).

        DELETE /api/mgmt/manual-entries/?member_id=<id>&date=YYYY-MM-DD
        """
        member_id = request.query_params.get('member_id')
        date_str = request.query_params.get('date')

        if not member_id or not date_str:
            return Response(
                {"error": "member_id und date sind erforderlich."},
                status=status.HTTP_400_BAD_REQUEST
            )

        employee = get_object_or_404(Employee, id=member_id)
        work_day = get_object_or_404(WorkDay, employee=employee, date=date_str)

        if is_month_locked(employee, work_day.date):
            month_formatted = work_day.date.strftime('%m/%Y')
            return Response(
                {"error": f"Der Monat {month_formatted} ist bereits abgeschlossen und kann nicht mehr bearbeitet werden."},
                status=status.HTTP_400_BAD_REQUEST
            )

        work_day.delete()
        return Response(
            {"detail": "Eintrag erfolgreich gelöscht."},
            status=status.HTTP_200_OK
        )

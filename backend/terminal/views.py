from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache 
from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from attendance.models import WorkDay, WorkSession
from core.models import Employee
from .serializers import TerminalUserSerializer

class TerminalUserListView(APIView):
    """Gibt die Liste aller aktiven Mitarbeiter für das Terminal zurück."""
    permission_classes = [AllowAny]

    def get(self, request):
        today = timezone.localdate()
        employees = Employee.objects.filter(is_active=True, is_superuser=False, joined_at__lte=today).order_by('last_name')
        serializer = TerminalUserSerializer(employees, many=True, context={'request': request})
        return Response(serializer.data)


class TerminalToggleStatusView(APIView):
    """Steuert das Ein- und Ausstempeln inkl. Sperrzeit-Logik."""
    permission_classes = [AllowAny]

    def post(self, request):
        employee_id = request.data.get('employee_id')
        chip_id = request.data.get('chip_id')
        today = timezone.localdate()

        # 1. Mitarbeiter finden (entweder über ID oder über RFID)
        if chip_id:
            # Bereinigung (Leerzeichen entfernen, in Großbuchstaben umwandeln)
            chip_id = chip_id.strip().upper()
            employee = Employee.objects.filter(chip_id=chip_id, is_active=True).first()
            
            if not employee:
                # <-- NEU: Unbekannter Chip! Wir merken uns die ID für 30 Sekunden im Cache fürs Anlernen
                cache.set('latest_unregistered_rfid', chip_id, timeout=30)
                
                return Response({
                    "status": "unknown_chip",
                    "error": "Unbekannter RFID-Chip!",
                    "chip_id": chip_id
                }, status=status.HTTP_404_NOT_FOUND)
                
        elif employee_id:
            employee = get_object_or_404(Employee, id=employee_id)
        else:
            return Response({"error": "Mitarbeiter-ID oder RFID-UID fehlt."}, status=status.HTTP_400_BAD_REQUEST)
            
        if employee.joined_at > today:
            return Response({"error": "Mitarbeiter ist noch nicht aktiv!"}, status=status.HTTP_400_BAD_REQUEST)

        disable_time = timedelta(seconds=60)

        # 1. WorkDay sicherstellen
        actual_work_day, _ = WorkDay.objects.get_or_create(
            employee=employee, 
            date=today,
            defaults={'day_type': 'work'}
        )

        # 2. Letzte Session für Timer-Check holen
        active_session = WorkSession.objects.filter(
            work_day=actual_work_day
        ).order_by('-check_in').first()

        # 3. Timer-Logik prüfen
        if active_session:
            last_action = active_session.check_out if active_session.check_out else active_session.check_in
            diff = timezone.localtime() - last_action
            
            if diff < disable_time:
                remaining_seconds = int((disable_time - diff).total_seconds())
                return Response({
                    "status": "warning", 
                    "message": "Bitte warte kurz zwischen dem Stempeln.", 
                    "remaining_seconds": remaining_seconds
                }, status=status.HTTP_200_OK)

        # 4. Abwesenheits-Check
        if actual_work_day.day_type in ['sick', 'vacation']:
            return Response(
                {"error": "Status Krank/Urlaub verhindert Check-In."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 5. Toggle Logik
        if active_session is None or active_session.check_out is not None:
            # NEU: Tag-Typ sofort auf 'work' setzen, falls er z.B. noch auf 'weekend' stand!
            if actual_work_day.day_type != 'work':
                actual_work_day.day_type = 'work'
                actual_work_day.save(update_fields=['day_type'])

            WorkSession.objects.create(work_day=actual_work_day, check_in=timezone.localtime())
            new_status = "Anwesend"
            msg_prefix = "Viel Erfolg"
        else:
            active_session.check_out = timezone.localtime()
            active_session.save()
            new_status = "Abwesend"
            msg_prefix = "Schönen Feierabend"
    
        return Response({
            "status": "success",
            "new_status": new_status,
            "username": employee.username,
            "employee_name": employee.first_name,
            "message": f"{msg_prefix}, {employee.first_name}!"
        }, status=status.HTTP_200_OK)
import os
import calendar
from datetime import date, timedelta
from django.utils import timezone
from django.http import FileResponse
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from attendance.models import WorkDay
from core.models import Employee, MonthlyPayout
from .models import EmployeeDocument

from management.permissions import IsSupervisor
from .serializers import (
    EmployeeDocumentSerializer, 
    AdminMonthlyReportOverviewSerializer,
    EmployeeMonthlyReportDetailSerializer
)



class EmployeeDocumentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Basis-Queryset je nach Rolle festlegen
        if request.user.is_staff:
            queryset = EmployeeDocument.objects.all()
        else:
            queryset = EmployeeDocument.objects.filter(employee=request.user)
            
        # 2. Filter nach employee_id über Query-Parameter (?employee_id=X)
        employee_id = request.query_params.get('employee_id')
        if employee_id:
            if request.user.is_staff:
                # Admins dürfen die Dokumente jedes Mitarbeiters filtern
                queryset = queryset.filter(employee_id=employee_id)
            else:
                # Sicherheit: Ein normaler Mitarbeiter darf hier nicht fremde IDs abfragen
                return Response({"detail": "Nicht autorisiert."}, status=status.HTTP_403_FOR_GRID)
        
        serializer = EmployeeDocumentSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


class EmployeeDocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, employee_id):
        # Nur Admins/Staff dürfen Dokumente hochladen
        if not request.user.is_staff:
            return Response({"detail": "Keine Berechtigung zum Hochladen von Dokumenten."}, status=403)
            
        employee = get_object_or_404(Employee, id=employee_id)
        file_obj = request.FILES.get('file')
        document_type = request.data.get('document_type', 'sonstiges')

        if not file_obj:
            return Response({"detail": "Keine Datei bereitgestellt."}, status=400)

        document = EmployeeDocument.objects.create(
            employee=employee,
            file=file_obj,
            original_filename=file_obj.name,
            document_type=document_type,
            uploaded_by = request.user
        )

        serializer = EmployeeDocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=201)


class EmployeeDocumentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, document_id):
        if not request.user.is_staff:
            return Response({"detail": "Keine Berechtigung zum Löschen von Dokumenten."}, status=403)
            
        document = get_object_or_404(EmployeeDocument, id=document_id)
        
        # Datei vom Speicher loeschen, falls vorhanden
        if document.file and os.path.isfile(document.file.path):
            os.remove(document.file.path)
            
        document.delete()
        return Response({"detail": "Dokument erfolgreich gelöscht."}, status=200)


class EmployeeDocumentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        document = get_object_or_404(EmployeeDocument, id=document_id)
        
        # Sicherheit: Nur Staff oder der Besitzer des Dokuments darf downloaden
        if not request.user.is_staff and document.employee != request.user:
            return Response({"detail": "Nicht autorisiert."}, status=403)

        if not document.file:
            return Response({"detail": "Datei nicht gefunden."}, status=404)

        response = FileResponse(document.file, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{document.original_filename}"'
        return response


class AdminMonthlyReportOverviewView(APIView):
    """
    Liefert eine Tabellen-Übersicht ALLER aktiven Mitarbeiter mit Soll-, Ist- 
    und Differenzstunden für ein bestimmtes Jahr und einen bestimmten Monat.
    """
    permission_classes = [IsSupervisor] 

    def get(self, request):
        now = timezone.localdate()
        try:
            year = int(request.query_params.get('year', now.year))
            month = int(request.query_params.get('month', now.month))
            if not (1 <= month <= 12):
                raise ValueError()
        except ValueError:
            return Response({"error": "Fehlende oder ungültige Parameter (year, month)."}, status=400)

        # Korrigierter Filter: Mitarbeiter auflisten, die zu dem Zeitpunkt schon im Betrieb waren
        target_date = date(year, month, 1)
        employees = Employee.objects.filter(
            is_active=True, 
            is_superuser=False, 
            joined_at__lte=target_date
        ).order_by('last_name', 'first_name')
        
        serializer = AdminMonthlyReportOverviewSerializer(
            employees, 
            many=True, 
            context={'year': year, 'month': month, 'request': request}
        )
        return Response(serializer.data)


class MonthlyReportDetailView(APIView):
    """
    Universeller Endpunkt für die PDF-Daten eines Monats.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee_id = request.query_params.get('employee_id')
        now = timezone.localdate()
        
        try:
            year = int(request.query_params.get('year', now.year))
            month = int(request.query_params.get('month', now.month))
            if not (1 <= month <= 12):
                raise ValueError()
        except ValueError:
            return Response({"error": "Fehlende oder ungültige Parameter (year, month)."}, status=400)

        if employee_id:
            if not (getattr(request.user, 'is_supervisor', False) or request.user.is_superuser):
                return Response({"detail": "Nicht autorisiert, die Daten anderer Mitarbeiter einzusehen."}, status=403)
            employee = get_object_or_404(Employee, id=employee_id)
        else:
            employee = request.user

        # --- NEU: Prüfen, ob der Monat bereits abgerechnet und verriegelt wurde ---
        is_locked = MonthlyPayout.objects.filter(
            employee=employee, year=year, month=month, is_processed=True
        ).exists()

        # Generiere Lücken im Kalendermonat NUR dann, wenn der Monat noch OFFEN ist.
        # Bei einem fixierten Abrechnungsmonat tasten wir die Datenbank nicht mehr an!
        if not is_locked:
            _, num_days = calendar.monthrange(year, month)
            start_date = date(year, month, 1)
            end_date = date(year, month, num_days)
            self._ensure_workdays_exist_for_range(employee, start_date, end_date)

        # Serializer ausgeben
        serializer = EmployeeMonthlyReportDetailSerializer(
            employee,
            context={'year': year, 'month': month, 'request': request, 'is_locked': is_locked}
        )
        return Response(serializer.data)

    def _resolve_day_type_for_new_workday(self, employee, current_date):
        """
        Bestimmt den day_type für einen frisch anzulegenden WorkDay.

        Basisannahme bleibt: Mo-Fr = Arbeitstag, Sa/So = Wochenende.
        ABER: individuelle Arbeitszeitschemata haben Vorrang – Mitarbeiter,
        die laut ihrem work_days_schema regulär samstags (oder sonntags)
        arbeiten, bekommen für diese Tage WORK statt WEEKEND. Damit landen
        sie korrekt als "Fehlzeit" statt fälschlich als "Wochenende", wenn
        sie an so einem Tag nicht stempeln.

        Werktage (Mo-Fr) bleiben bewusst immer WORK, unabhängig vom Schema –
        Teilzeit-freie Wochentage sind ein separates Thema und hier nicht
        Teil der Umstellung.
        """
        is_calendar_weekend = current_date.weekday() >= 5

        if not is_calendar_weekend:
            return WorkDay.DayType.WORK

        scheduled_hours = 0.0
        if hasattr(employee, 'get_scheduled_hours_for_date'):
            scheduled_hours = employee.get_scheduled_hours_for_date(current_date) or 0.0

        return WorkDay.DayType.WORK if scheduled_hours > 0 else WorkDay.DayType.WEEKEND

    def _ensure_workdays_exist_for_range(self, user, start_date, end_date):
        today = timezone.localdate()
        effective_end_date = min(end_date, today)

        if start_date > effective_end_date:
            return

        existing_dates = set(
            WorkDay.objects.filter(
                employee=user, 
                date__range=[start_date, effective_end_date]
            ).values_list('date', flat=True)
        )

        new_workdays = []
        current_date = start_date
        
        while current_date <= effective_end_date:
            if current_date not in existing_dates:
                temp_wd = WorkDay(employee=user, date=current_date)
                temp_wd.day_type = self._resolve_day_type_for_new_workday(user, current_date)
                new_workdays.append(temp_wd)
            
            current_date += timedelta(days=1)

        if new_workdays:
            WorkDay.objects.bulk_create(new_workdays)
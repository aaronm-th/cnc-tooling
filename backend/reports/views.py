import os

from rest_framework import status, permissions
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from django.http import FileResponse

from attendance.models import WorkSession, WorkDay
from .models import EmployeeDocument
from core.models import Employee

from .serializers import WorkSessionSerializer, WorkDayWithSessionsSerializer, EmployeeDocumentSerializer
from django.utils.dateparse import parse_date
from datetime import date, timedelta

from django.shortcuts import get_object_or_404

class EmployeeDocumentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Basis-Queryset je nach Rolle festlegen
        if request.user.is_staff:
            queryset = EmployeeDocument.objects.all()
        else:
            queryset = EmployeeDocument.objects.filter(employee=request.user)
            
        # 2. NEU: Filter nach employee_id über Query-Parameter (?employee_id=X)
        employee_id = request.query_params.get('employee_id')
        if employee_id:
            if request.user.is_staff:
                # Admins dürfen die Dokumente jedes Mitarbeiters filtern
                queryset = queryset.filter(employee_id=employee_id)
            else:
                # Sicherheit: Ein normaler Mitarbeiter darf hier nicht die IDs anderer abfragen
                if str(request.user.id) != str(employee_id):
                    return Response(
                        {"detail": "Nicht autorisiert, Dokumente anderer Mitarbeiter einzusehen."}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        # Sortierung hinzufügen (neueste Dokumente zuerst)
        queryset = queryset.order_by('-uploaded_at')

        # Serialisierung der Daten
        serializer = EmployeeDocumentSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class EmployeeDocumentUploadView(APIView):
    # Nur Admins oder Supervisors sollten Dokumente für Mitarbeiter hochladen dürfen
    permission_classes = [permissions.IsAuthenticated] 

    def post(self, request, member_id):
        # 1. Mitarbeiter holen, für den das Dokument bestimmt ist
        employee = get_object_or_404(Employee, id=member_id)
        
        # 2. Daten aus dem FormData (request.FILES und request.data) extrahieren
        uploaded_file = request.FILES.get('document')
        document_type = request.data.get('document_type')

        # 3. Validierung
        if not uploaded_file:
            return Response(
                {"detail": "Es wurde keine Datei hochgeladen."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not document_type:
            return Response(
                {"detail": "Der Dokumententyp fehlt."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validierung des Dateityps (Backend-Schutz)
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in ['.pdf', '.png', '.jpg', '.jpeg']:
            return Response(
                {"detail": "Ungültiges Dateiformat. Nur PDF, PNG und JPG erlaubt."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validierung der Dateigröße (5 MB)
        if uploaded_file.size > 5 * 1024 * 1024:
            return Response(
                {"detail": "Datei ist zu groß. Maximal 5 MB erlaubt."}, 
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        try:
            # 4. Dokumenten-Instanz erstellen und speichern
            document = EmployeeDocument.objects.create(
                employee=employee,
                document_type=document_type,
                file=uploaded_file,
                original_filename=uploaded_file.name,
                uploaded_by=request.user # Wer hat die Datei hochgeladen?
            )
            
            return Response({
                "status": "success",
                "message": "Dokument erfolgreich hochgeladen.",
                "document_id": document.id,
                "filename": document.original_filename
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"detail": f"Interner Fehler beim Speichern: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EmployeeDocumentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id):
        # Dokument holen
        document = get_object_or_404(EmployeeDocument, id=document_id)
        
        # Sicherheit: Gehört das Dokument dem eingeloggten User?
        # (Erweitere dies um `or request.user.is_staff`, falls Admins auch downloaden dürfen)
        if document.employee != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Nicht autorisiert, dieses Dokument anzuzeigen."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        try:
            # Datei öffnen und als Download streamen
            # as_attachment=True sorgt dafür, dass im Browser der "Speichern unter"-Dialog kommt
            response = FileResponse(
                document.file.open('rb'), 
                as_attachment=True, 
                filename=document.original_filename
            )
            return response
        except Exception as e:
            return Response(
                {"detail": f"Fehler beim Laden der Datei: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EmployeeDocumentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, document_id):
        # Dokument holen
        document = get_object_or_404(EmployeeDocument, id=document_id)
        
        # Sicherheit: Nur Admins/Staff oder der Eigentümer (falls erlaubt) dürfen löschen
        # Meistens dürfen Mitarbeiter Dokumente nicht selbst löschen, daher hier primär is_staff
        if not request.user.is_staff and document.uploaded_by != request.user:
            return Response(
                {"detail": "Nicht autorisiert, dieses Dokument zu löschen."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        try:
            # Physische Datei vom Speichermedium löschen
            if document.file:
                if os.path.isfile(document.file.path):
                    os.remove(document.file.path)
            
            # Datenbank-Eintrag löschen
            document.delete()
            
            return Response(
                {"status": "success", "message": "Dokument erfolgreich gelöscht."}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"detail": f"Fehler beim Löschen der Datei: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MonthlyWorkSessionListView(ListAPIView):
    serializer_class = WorkSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = WorkSession.objects.filter(work_day__employee=user)

        # Parameter aus der URL extrahieren (start & end)
        start_date_str = self.request.query_params.get('start')
        end_date_str = self.request.query_params.get('end')

        if start_date_str and end_date_str:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            
            if start_date and end_date:
                # Wir filtern über das Datum des verknüpften WorkDay
                queryset = queryset.filter(
                    work_day__date__range=[start_date, end_date]
                )

        return queryset.order_by('check_in')
    



class MonthlyWorkDayListView(ListAPIView):
    serializer_class = WorkDayWithSessionsSerializer
    permission_classes = [IsAuthenticated]

    # MonthlyWorkDayListView

    def get_queryset(self):
        user = self.request.user
        joined_at = user.joined_at.date() if hasattr(user.joined_at, 'date') else user.joined_at        
        
        start_date_str = self.request.query_params.get('start')
        end_date_str = self.request.query_params.get('end')
        
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)

        if start_date and joined_at:
            first_day_of_joined_month = date(joined_at.year, joined_at.month, 1)
            if start_date < first_day_of_joined_month:
                raise ValidationError("Zeitraum vor Eintrittsmonat.")

            if start_date < joined_at:
                start_date = joined_at

        # Ab hier arbeitet die Methode mit dem korrigierten start_date
        if start_date and end_date:
            self._ensure_workdays_exist(user, start_date, end_date)

        return WorkDay.objects.filter(
                employee=user, 
                date__range=[start_date, end_date]
            ).select_related('employee')\
            .prefetch_related('sessions')\
            .order_by('date')
    


    def _ensure_workdays_exist(self, user, start_date, end_date):
        """
        Prüft auf Lücken im Zeitraum und erstellt fehlende WorkDay-Objekte.
        Erstellt Tage in der Zukunft nur bis zum heutigen Datum.
        """
        # 1. Begrenzung: Wir erstellen Tage maximal bis HEUTE
        today = date.today()
        effective_end_date = min(end_date, today)

        # Falls das Startdatum bereits in der Zukunft liegt, direkt abbrechen
        if start_date > effective_end_date:
            return

        # Alle vorhandenen Daten in diesem eingeschränkten Zeitraum holen
        existing_dates = set(
            WorkDay.objects.filter(
                employee=user, 
                date__range=[start_date, effective_end_date]
            ).values_list('date', flat=True)
        )

        new_workdays = []
        current_date = start_date
        
        # Schleife läuft nur bis zum effective_end_date
        while current_date <= effective_end_date:
            if current_date not in existing_dates:
                temp_wd = WorkDay(employee=user, date=current_date)
                temp_wd.day_type = temp_wd.determine_type()
                new_workdays.append(temp_wd)
            
            current_date += timedelta(days=1)

        if new_workdays:
            WorkDay.objects.bulk_create(new_workdays)
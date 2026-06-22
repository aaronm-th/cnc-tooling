from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.generics import RetrieveUpdateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status, viewsets, mixins
from django.contrib import auth
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .serializers import (
    EmployeeSerializer, UserLoginResponseSerializer, 
    UserStatsSerializer, SimpleResponseSerializer, NotificationSerializer
)

from .models import Employee, VacationQuota, Notification, Invitation, Scratchpad, TodoItem

from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from django.utils import timezone





User = get_user_model()



# Hilfsfunktion bleibt gleich
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(responses={200: UserLoginResponseSerializer})
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = auth.authenticate(username=email, password=password)

        if user is not None:
            tokens = get_tokens_for_user(user)
            serializer = EmployeeSerializer(user, context={'request': request})
            return Response({
                'success': True,
                'user': serializer.data,
                'tokens': tokens
            })
        return Response(
            {'success': False, 'message': 'Ungültige E-Mail oder Passwort'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )



class RegisterView(APIView):
    # Muss für unregistrierte Mitarbeiter offen sein
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: SimpleResponseSerializer, 400: SimpleResponseSerializer},
        description="Schließt die Registrierung eines eingeladenen Mitarbeiters ab."
    )

    def get(self, request):
        token_str = request.query_params.get('token')
        if not token_str:
            return Response({'valid': False, 'message': 'Kein Token übergeben.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Unsichtbare Zeichen entfernen
        token_str = str(token_str).strip().replace('\u2060', '')

        try:
            invitation = Invitation.objects.get(token=token_str)
            if invitation.is_valid:
                return Response({
                    'valid': True,
                    'firstname': invitation.employee.first_name,
                    'lastname': invitation.employee.last_name,
                    'email': invitation.employee.email
                 }, status=status.HTTP_200_OK)
        except (Invitation.DoesNotExist, ValueError, ValidationError):
            return Response({
                'valid': False, 
                'message': 'Der Einladungs-Link ist ungültig oder abgelaufen.'
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({'valid': False, 'message': 'Der Einladungs-Link ist ungültig oder abgelaufen.'}, status=status.HTTP_400_BAD_REQUEST)


    def post(self, request):
        data = request.data
        token_str = data.get('token')

        if token_str:
            token_str = str(token_str).strip().replace('\u2060', '')
        
        password = data.get('password')
        
        # Vor- und Nachname, Telefonnummer etc. kommen jetzt aus dem Onboarding-Formular
        first_name = data.get('firstname')
        last_name = data.get('lastname')
        phone = data.get('phone')
        # avatar = request.FILES.get('avatar') # Falls du direkt ein Bild hochlädst

        # 1. Validierung der Mindestanforderungen
        if not token_str or not password:
            return Response({
                'success': False, 
                'message': 'Token und Passwort sind erforderlich.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 2. Token in der Datenbank suchen
        try:
            invitation = Invitation.objects.get(token=token_str)
        except (Invitation.DoesNotExist, ValueError, ValidationError):
            return Response({
                'success': False, 
                'message': 'Ungültiges Einladungs-Token.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 3. Prüfen, ob das Token noch gültig ist
        if not invitation.is_valid:
            return Response({
                'success': False, 
                'message': 'Dieses Token ist abgelaufen oder wurde bereits verwendet.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 4. Bestehenden User holen, aktivieren und updaten
        user = invitation.employee
        user.set_password(password)
        user.first_name = first_name if first_name else user.first_name
        user.last_name = last_name if last_name else user.last_name
        user.is_active = True  # Jetzt darf er sich einloggen!
        user.save()

        # 5. Optionale Onboarding-Daten im Profil speichern
        if hasattr(user, 'profile'):
            profile = user.profile
            if phone:
                profile.phone = phone
            # if avatar:
            #     profile.avatar = avatar
            profile.save()

        # 6. Token entwerten, damit es kein zweites Mal genutzt werden kann
        invitation.is_used = True
        invitation.save()

        return Response({
            'success': True, 
            'message': 'Registrierung erfolgreich abgeschlossen. Du kannst dich jetzt einloggen.'
        }, status=status.HTTP_200_OK)
    

class EmployeeListView(ListAPIView):
    """Gibt eine Liste aller aktiven Mitarbeiter zurück."""
    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.filter(is_active=True).order_by('last_name')


class UserProfileView(RetrieveUpdateAPIView):
    """Check-Auth (GET) und Profil-Update (PATCH) kombiniert."""
    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeSerializer

    def get_object(self):
        # Statt einer ID in der URL nehmen wir immer den eingeloggten User
        return self.request.user

    def update(self, request, *args, **kwargs):
        # Deine Spezial-Logik für Foto und Passwort bleibt erhalten
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Foto-Handling
        if 'photo' in request.FILES:
            instance.photo = request.FILES['photo']
            
        # Passwort-Handling
        password = request.data.get('password')
        if password:
            instance.set_password(password)
            
        serializer.save()
        return Response({
            "message": "Erfolgreich gespeichert",
            "user": serializer.data
        })

class UserStatsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserStatsSerializer})
    def get(self, request):
        # Da Employee von AbstractUser erbt, ist request.user bereits der Employee!
        employee = request.user
        
        # Übergib das Employee-Objekt direkt an den Serializer
        serializer = UserStatsSerializer(employee, context={'request': request})
        return Response(serializer.data)
    

class ScratchpadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: SimpleResponseSerializer})
    def get(self, request):
        scratchpad, created = Scratchpad.objects.get_or_create(employee=request.user)

        return Response({'notes': scratchpad.content}, status=status.HTTP_200_OK)

    @extend_schema(request=SimpleResponseSerializer, responses={200: SimpleResponseSerializer})
    def put(self, request):
        """Aktualisiert die Notizen."""
        notes = request.data.get('notes', '')

        Scratchpad.objects.update_or_create(
            employee=request.user,
            defaults={'content': notes}
        )

        request.user.scratchpad.content = notes
        request.user.scratchpad.updated_at = timezone.now()
        request.user.scratchpad.save()
        return Response({'success': True, 'message': 'Notizen aktualisiert', 'notes': notes})


class TodoView(APIView):
    permission_classes = [IsAuthenticated]

    # 1. Alle To-Dos des Users laden
    def get(self, request):
        todos = TodoItem.objects.filter(employee=request.user)
        # Manuelle Serialisierung, da es sich um ein simples Modell handelt
        todo_list = [{"id": t.id, "text": t.text, "completed": t.completed} for t in todos]
        return Response(todo_list, status=status.HTTP_200_OK)

    # 2. Ein neues To-Do anlegen
    def post(self, request):
        text = request.data.get("text", "").strip()
        if not text:
            return Response({"error": "Text darf nicht leer sein"}, status=status.HTTP_400_BAD_REQUEST)
        
        todo = TodoItem.objects.create(employee=request.user, text=text)
        return Response({"id": todo.id, "text": todo.text, "completed": todo.completed}, status=status.HTTP_201_CREATED)

    # 3. Den Status (erledigt/offen) updaten
    def put(self, request):
        todo_id = request.data.get("id")
        try:
            todo = TodoItem.objects.get(id=todo_id, employee=request.user)
            todo.completed = request.data.get("completed", todo.completed)
            todo.save()
            return Response({"status": "updated"}, status=status.HTTP_200_OK)
        except TodoItem.DoesNotExist:
            return Response({"error": "Nicht gefunden"}, status=status.HTTP_404_NOT_FOUND)

    # 4. Ein To-Do löschen
    def delete(self, request):
        todo_id = request.data.get("id") or request.query_params.get("id")
        try:
            todo = TodoItem.objects.get(id=todo_id, employee=request.user)
            todo.delete()
            return Response({"status": "deleted"}, status=status.HTTP_200_OK)
        except TodoItem.DoesNotExist:
            return Response({"error": "Nicht gefunden"}, status=status.HTTP_404_NOT_FOUND)


class NotificationViewSet(mixins.ListModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    """
    ViewSet für Benachrichtigungen:
    - GET /api/notifications/ -> Liste
    - PATCH /api/notifications/id/ -> Einzelne als gelesen markieren
    - DELETE /api/notifications/id/ -> Soft-Delete einzeln
    - PATCH /api/notifications/mark_all_as_read/ -> Alle als gelesen markieren
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user, 
            is_deleted_by_user=False
        ).order_by('-created_at')

    def perform_destroy(self, instance):
        # Soft-Delete
        instance.is_deleted_by_user = True
        instance.save()

    # --- CUSTOM ACTIONS ---

    @extend_schema(responses={200: SimpleResponseSerializer})
    @action(detail=False, methods=['patch'], url_path='mark-all-as-read')
    def mark_all_as_read(self, request):
        """Markiert alle Benachrichtigungen des Users als gelesen."""
        self.get_queryset().filter(read=False).update(read=True)
        return Response({'success': True, 'message': 'All marked as read'})

    @extend_schema(responses={204: None})
    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request):
        """Löscht alle Benachrichtigungen des Users (Soft-Delete)."""
        self.get_queryset().update(is_deleted_by_user=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
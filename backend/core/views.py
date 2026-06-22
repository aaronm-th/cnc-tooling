import calendar
import datetime
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Employee, Notification, Scratchpad, TodoItem, VacationQuota
from .serializers import (
    EmployeeSerializer,
    NotificationSerializer,
    SimpleResponseSerializer,
    UserLoginResponseSerializer,
    UserStatsSerializer,
)

User = get_user_model()


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
        username = request.data.get('username')
        password = request.data.get('password')
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            tokens = get_tokens_for_user(user)
            serializer = EmployeeSerializer(user, context={'request': request})
            return Response({
                'success': True,
                'user': serializer.data,
                'tokens': tokens
            })
        return Response(
            {'success': False, 'message': 'Ungültiger Benutzername oder Passwort'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )


class EmployeeListView(ListAPIView):
    """Gibt eine Liste aller aktiven Mitarbeiter zurück."""
    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.filter(is_active=True).order_by('last_name')


class UserProfileView(RetrieveUpdateAPIView):
    """Profil-Ansicht (GET) und Profil-Update (PATCH). 
    Hier kann der Mitarbeiter sein Initialpasswort ändern."""
    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Foto-Handling
        if 'photo' in request.FILES:
            instance.photo = request.FILES['photo']
            
        # Passwort-Handling (Erlaubt die Änderung des Initialpassworts)
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
        employee = request.user
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
        notes = request.data.get('notes', '')

        scratchpad, _ = Scratchpad.objects.update_or_create(
            employee=request.user,
            defaults={'content': notes}
        )
        return Response({'success': True, 'message': 'Notizen aktualisiert', 'notes': notes})


class TodoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        todos = TodoItem.objects.filter(employee=request.user)
        todo_list = [{"id": t.id, "text": t.text, "completed": t.completed} for t in todos]
        return Response(todo_list, status=status.HTTP_200_OK)

    def post(self, request):
        text = request.data.get("text", "").strip()
        if not text:
            return Response({"error": "Text darf nicht leer sein"}, status=status.HTTP_400_BAD_REQUEST)
        
        todo = TodoItem.objects.create(employee=request.user, text=text)
        return Response({"id": todo.id, "text": todo.text, "completed": todo.completed}, status=status.HTTP_201_CREATED)

    def put(self, request):
        todo_id = request.data.get("id")
        try:
            todo = TodoItem.objects.get(id=todo_id, employee=request.user)
            todo.completed = request.data.get("completed", todo.completed)
            todo.save()
            return Response({"status": "updated"}, status=status.HTTP_200_OK)
        except TodoItem.DoesNotExist:
            return Response({"error": "Nicht gefunden"}, status=status.HTTP_404_NOT_FOUND)

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
    Schlankes ViewSet für Benachrichtigungen (Hard-Delete statt Soft-Delete)
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')

    @extend_schema(responses={200: SimpleResponseSerializer})
    @action(detail=False, methods=['patch'], url_path='mark-all-as-read')
    def mark_all_as_read(self, request):
        """Markiert alle Benachrichtigungen des Users als gelesen."""
        self.get_queryset().filter(read=False).update(read=True)
        return Response({'success': True, 'message': 'All marked as read'})

    @extend_schema(responses={204: None})
    @action(detail=False, methods=['delete'], url_path='delete-all')
    def delete_all(self, request):
        """Löscht alle Benachrichtigungen des Users endgültig aus der DB."""
        self.get_queryset().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
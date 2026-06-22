from rest_framework import permissions

class IsSupervisor(permissions.BasePermission):
    def has_permission(self, request, view):
        # Nur Supervisor dürfen durch
        return bool(request.user and request.user.is_authenticated and request.user.is_supervisor)
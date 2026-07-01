from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from django.views.decorators.csrf import csrf_exempt
from .views import (
    CustomLoginView, EmployeeListView, 
    UserProfileView, UserStatsView, NotificationViewSet, ScratchpadView, TodoView
)

# 1. Router für ViewSets erstellen
router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # AUTHENTIFIZIERUNG
    path('api/login/', csrf_exempt(CustomLoginView.as_view()), name='login'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # NUTZERDATEN & PROFIL
    # Wir nutzen UserProfileView für GET (check) und PATCH (update)
    path('api/user/check/', UserProfileView.as_view(), name='api_check_auth'),
    path('api/user/update/', UserProfileView.as_view(), name='api_update_profile'),
    path('api/users/all/', EmployeeListView.as_view(), name='all_employees'),
    path('api/user-stats/', UserStatsView.as_view(), name='user_stats'),
    path('api/user/scratchpad/', ScratchpadView.as_view(), name='user_scratchpad'),
    path('api/user/todos/', TodoView.as_view(), name='user-todos'),

    # BENACHRICHTIGUNGEN (Router-URLs einbinden)
    # Das deckt automatisch /api/notifications/ UND /api/notifications/id/ ab
    path('api/', include(router.urls)),
]
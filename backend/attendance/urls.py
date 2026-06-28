from django.urls import path
from . import views

urlpatterns = [
    # --- Urlaub / Leave Requests ---
    path('api/leave-request/', views.LeaveRequestListCreateAPIView.as_view(), name='leave-list'),
    path('api/leave-request/<int:pk>/', views.LeaveRequestDetailAPIView.as_view(), name='leave-detail'),

    # --- Korrekturanträge & Session-Details ---
    path('api/change-request/', views.ChangeRequestListAPIView.as_view(), name='change-list'),
    path('api/work-session-request/<int:pk>/', views.WorkSessionRequestAPIView.as_view(), name='work-session-request'),

    # --- Tagesansicht ---
    path('api/workday-details/<int:pk>/', views.WorkDaySessionsAPIView.as_view(), name='workday-details'),
    path('api/work-day-request/<int:pk>/', views.WorkDayRequestAPIView.as_view(), name='work-day-request'),


    
]
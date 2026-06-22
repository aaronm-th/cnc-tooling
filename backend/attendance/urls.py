from django.urls import path
from . import views

urlpatterns = [
    # --- Urlaub / Leave Requests ---
    # GET (Liste) & POST (Erstellen)
    path('api/leave-request/', views.LeaveRequestListCreateAPIView.as_view(), name='leave-list'),
    # PUT (Update) & DELETE (Stornieren)
    path('api/leave-request/<int:pk>/', views.LeaveRequestDetailAPIView.as_view(), name='leave-detail'),

    # --- Stempeln / Work Sessions ---
    # GET (Status) & POST (Ein-/Ausstempeln)
    #path('api/work-sessions/', views.WorkSessionToggleAPIView.as_view(), name='work-session-toggle'),

    # --- Korrekturanträge & Session-Details ---
    # GET (Details), POST (Korrektur einreichen), DELETE (Korrektur löschen)
    # Da die View die ID zwingend braucht, nutzen wir nur den Pfad mit <int:pk>
    path('api/change-request/', views.ChangeRequestListAPIView.as_view(), name='change-list'),
    path('api/work-session-request/<int:pk>/', views.WorkSessionRequestAPIView.as_view(), name='work-session-request'),

    # --- Tagesansicht ---
    # GET (Alle Sessions eines Tages)
    path('api/workday-details/<int:pk>/', views.WorkDaySessionsAPIView.as_view(), name='workday-details'),

    path('api/work-day-request/<int:pk>/', views.WorkDayRequestAPIView.as_view(), name='work-day-request'),
]
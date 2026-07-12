from django.urls import path
from .views import (
    SupervisorDashboardStatsView, TeamMemberListView, TeamMemberDetailView,
    HandleLeaveRequestView, HandleChangeRequestView,
    TeamCalendarEventsView, CreateEditEmployeeView, ManualEntriesView,
    CloseMonthGlobalView, CloseEmployeeMonthView, ReopenEmployeeMonthView, PendingChipView
)

urlpatterns = [
    path('api/mgmt/stats/', SupervisorDashboardStatsView.as_view(), name='mgmt-stats'),

    path('api/mgmt/team/', TeamMemberListView.as_view(), name='team-list'),
    path('api/mgmt/team/new/', CreateEditEmployeeView.as_view(), name='team-detail'),
    path('api/mgmt/team/<int:pk>/', TeamMemberDetailView.as_view(), name='team-detail'),
    path('api/mgmt/manual-entries/', ManualEntriesView.as_view(), name='manual-entries'),
    path('mgmt/pending-chip/', PendingChipView.as_view(), name='pending-chip'),
    
    path('api/mgmt/leave-requests/', HandleLeaveRequestView.as_view(), name='mgmt-leave-requests'),
    path('api/mgmt/change-requests/', HandleChangeRequestView.as_view(), name='mgmt-change-requests'),
    
    path('api/mgmt/calendar-events/', TeamCalendarEventsView.as_view(), name='mgmt-calendar-events'),

    # --- NEU: Monatsabschluss & Auszahlungs-Sperren ---
    path('api/mgmt/payouts/close-month/', CloseMonthGlobalView.as_view(), name='payout-close-month-global'),
    path('api/mgmt/payouts/close-employee/', CloseEmployeeMonthView.as_view(), name='payout-close-employee'),
    path('api/mgmt/payouts/reopen-employee/', ReopenEmployeeMonthView.as_view(), name='payout-reopen-employee'),
]
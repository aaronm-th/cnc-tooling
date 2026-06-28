from django.urls import path
from .views import (
    SupervisorDashboardStatsView, TeamMemberListView, TeamMemberDetailView,
    HandleLeaveRequestView, HandleChangeRequestView,
    TeamCalendarEventsView, CreateEditEmployeeView, ManualEntriesView
)

urlpatterns = [
    path('api/mgmt/stats/', SupervisorDashboardStatsView.as_view(), name='mgmt-stats'),

    path('api/mgmt/team/', TeamMemberListView.as_view(), name='team-list'),
    path('api/mgmt/team/new/', CreateEditEmployeeView.as_view(), name='team-detail'),
    path('api/mgmt/team/<int:pk>/', TeamMemberDetailView.as_view(), name='team-detail'),
    path('api/mgmt/manual-entries/', ManualEntriesView.as_view(), name='manual-entries'),
    
    path('api/mgmt/leave-requests/', HandleLeaveRequestView.as_view(), name='mgmt-leave-requests'),
    path('api/mgmt/change-requests/', HandleChangeRequestView.as_view(), name='mgmt-change-requests'),
    
    path('api/mgmt/calendar-events/', TeamCalendarEventsView.as_view(), name='mgmt-calendar-events'),
]
from django.urls import path
from .views import TerminalUserListView, TerminalToggleStatusView

urlpatterns = [
    path('api/terminal/users/', TerminalUserListView.as_view(), name='terminal-users'),
    path('api/terminal/toggle/', TerminalToggleStatusView.as_view(), name='terminal-toggle'),
]
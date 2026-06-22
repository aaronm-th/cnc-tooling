from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import UserCalendarFeedView

urlpatterns = [
    path('api/user-calendar/', UserCalendarFeedView.as_view(), name='user_calendar_feed'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
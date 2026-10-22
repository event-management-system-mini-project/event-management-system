from django.urls import path

from .auth_views import login_view, logout_view, session_view
from .event_views import list_own_events

urlpatterns = [
    path("auth/session", session_view),
    path("auth/login", login_view),
    path("auth/logout", logout_view),
    path("organizer/events", list_own_events),
]

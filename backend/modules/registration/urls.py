from django.urls import path
from .views import register_attendee

urlpatterns = [
    path("events/<uuid:event_id>/register", register_attendee, name="register-attendee"),
]

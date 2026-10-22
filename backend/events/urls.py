from django.urls import path
from .views import register_attendee

urlpatterns = [
    # ... your other event paths ...
    path("events/<uuid:event_id>/register", register_attendee, name="register-attendee"),
]
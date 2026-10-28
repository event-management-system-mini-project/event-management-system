from django.urls import path
from .views import register_attendee, event_registrations_list

urlpatterns = [
    path("events/<uuid:event_id>/register/", register_attendee, name="register-attendee"),
    path("events/<uuid:event_id>/registrations/", event_registrations_list, name="event-registrations-list"),
]
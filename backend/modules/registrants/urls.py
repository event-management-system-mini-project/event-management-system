from django.urls import path
from .views import event_registrations_list

urlpatterns = [
    path("events/<uuid:event_id>/registrations/", event_registrations_list, name="event-registrations-list"),
]
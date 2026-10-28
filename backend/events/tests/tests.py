import time
from datetime import date, time as dtime
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from events.models import Event, Registration, Organizer

class EventRegistrationIssuesTests(APITestCase):
    def setUp(self):
        self.organizer = Organizer.objects.create_user(
            username="testorganizer", password="password123"
        )
        self.event = Event.objects.create(
            name="Tech Summit 2026",
            description="A summit on future tech.",
            date=date(2028, 12, 31),
            time=dtime(10, 0),
            location="Online",
            organizer=self.organizer
        )
        self.register_url = reverse("register-attendee", kwargs={"event_id": self.event.id})
        self.list_url = reverse("event-registrations-list", kwargs={"event_id": self.event.id})

    def test_anonymous_and_non_owner_access_rejected(self):
        response_anon = self.client.get(self.list_url)
        self.assertEqual(response_anon.status_code, status.HTTP_403_FORBIDDEN)

        response_nonowner = self.client.get(self.list_url, {"organizer_id": "wrong-org"})
        self.assertEqual(response_nonowner.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_view_registrant_list(self):
        Registration.objects.create(event=self.event, name="John Doe", email="john@example.com")

        response = self.client.get(self.list_url, HTTP_X_ORGANIZER_ID=str(self.organizer.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["registration_count"], 1)
        self.assertEqual(response.data["registrants"][0]["email"], "john@example.com")

    def test_registration_performance_under_3_seconds(self):
        start_time = time.time()
        response = self.client.post(self.register_url, {
            "name": "Jane Doe",
            "email": "jane@example.com"
        })
        duration = time.time() - start_time

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertLess(duration, 3.0, "Registration response took longer than 3 seconds.")
import time
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Event, Registration

class EventRegistrationIssuesTests(APITestCase):
    def setUp(self):
        self.event = Event.objects.create(
            title="Tech Summit 2026",
            organizer_id="org-123",
            date="2026-12-31T10:00:00Z"
        )
        self.register_url = reverse("register-attendee", kwargs={"event_id": self.event.id})
        self.list_url = reverse("event-registrations-list", kwargs={"event_id": self.event.id})

    # --- Issue #14 & #15 Access Control & Privacy Checks ---
    def test_anonymous_and_non_owner_access_rejected(self):
        # Anonymous attempt (No header/query parameter)
        response_anon = self.client.get(self.list_url)
        self.assertEqual(response_anon.status_code, status.HTTP_403_FORBIDDEN)

        # Non-owner attempt (Mismatched organizer_id)
        response_nonowner = self.client.get(self.list_url, {"organizer_id": "wrong-org"})
        self.assertEqual(response_nonowner.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_view_registrant_list(self):
        # Create synthetic registration
        Registration.objects.create(event=self.event, name="John Doe", email="john@example.com")

        # Owner request with matching header
        response = self.client.get(self.list_url, HTTP_X_ORGANIZER_ID="org-123")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["registration_count"], 1)
        self.assertEqual(response.data["registrants"][0]["email"], "john@example.com")

    # --- Issue #19 Performance Requirement (Action under 3 seconds) ---
    def test_registration_performance_under_3_seconds(self):
        start_time = time.time()
        response = self.client.post(self.register_url, {
            "name": "Jane Doe",
            "email": "jane@example.com"
        })
        duration = time.time() - start_time

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertLess(duration, 3.0, "Registration response took longer than 3 seconds.")
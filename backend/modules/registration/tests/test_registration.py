"""Route-level checks for the attendee registration module."""

import json
from datetime import timedelta
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from events.models import Event, Organizer, Registration


class RegistrationRouteTests(TestCase):
    def setUp(self):
        self.organizer = Organizer.objects.create_user(
            username="registration-owner", password="synthetic-password"
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            name="Synthetic Registration Event",
            description="Synthetic event for registration route tests.",
            date=timezone.localdate() + timedelta(days=30),
            time="10:00:00",
            location="Synthetic Hall",
        )

    def post(self, event_id, payload):
        return self.client.post(
            f"/api/events/{event_id}/register",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_valid_registration_is_stored_and_returned(self):
        response = self.post(
            self.event.id,
            {"name": "Synthetic Attendee", "email": "attendee@example.com"},
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["name"], "Synthetic Attendee")
        self.assertEqual(body["event"], str(self.event.id))
        self.assertEqual(Registration.objects.count(), 1)
        self.assertEqual(Registration.objects.get().email, "attendee@example.com")

    def test_duplicate_email_returns_a_clear_error_and_no_second_record(self):
        payload = {"name": "Synthetic Attendee", "email": "attendee@example.com"}
        self.assertEqual(self.post(self.event.id, payload).status_code, 201)
        response = self.post(self.event.id, payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already registered", response.json()["detail"])
        self.assertEqual(Registration.objects.count(), 1)

    def test_missing_fields_are_rejected_without_a_record(self):
        response = self.post(self.event.id, {"name": "", "email": ""})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Registration.objects.count(), 0)

    def test_unknown_event_returns_404_without_a_record(self):
        response = self.post(
            uuid4(), {"name": "Synthetic", "email": "attendee@example.com"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Registration.objects.count(), 0)

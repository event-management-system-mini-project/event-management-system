
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from events.models import Event, Organizer, Registration


class UpcomingEventsTests(TestCase):
    def setUp(self):
        self.organizer = Organizer.objects.create_user(
            username="browsing-test-owner",
            password="test-password",
        )

    def create_event(self, name, date, time):
        return Event.objects.create(
            organizer=self.organizer,
            name=name,
            description="Synthetic test event",
            date=date,
            time=time,
            location="Test Hall",
        )

    def test_events_are_sorted_by_date_and_time(self):
        today = timezone.localdate()

        self.create_event("Later", today + timedelta(days=2), "10:00:00")
        self.create_event("Earlier", today + timedelta(days=1), "15:00:00")
        self.create_event("First", today + timedelta(days=1), "09:00:00")

        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)
        names = [event["name"] for event in response.json()["events"]]
        self.assertEqual(names, ["First", "Earlier", "Later"])

    def test_past_events_are_excluded(self):
        today = timezone.localdate()

        # Create a valid future event first.
        past_event = self.create_event(
            "Past",
            today + timedelta(days=1),
            "12:00:00",
        )

        # Simulate an existing database record that is now in the past.
        Event.objects.filter(pk=past_event.pk).update(
            date=today - timedelta(days=1)
        )

        future_event = self.create_event(
            "Future",
            today + timedelta(days=2),
            "12:00:00",
        )

        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)
        names = [event["name"] for event in response.json()["events"]]

        self.assertNotIn("Past", names)
        self.assertIn("Future", names)

    def test_registration_count_is_included_without_personal_data(self):
        event = self.create_event(
            "Counted event",
            timezone.localdate() + timedelta(days=2),
            "10:00:00",
        )

        Registration.objects.create(
            event=event,
            name="Synthetic Attendee",
            email="synthetic@example.com",
        )

        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)

        item = next(
            event_data
            for event_data in response.json()["events"]
            if event_data["id"] == str(event.id)
        )

        self.assertEqual(item["registration_count"], 1)
        self.assertNotIn("email", item)
        self.assertNotIn("registrants", item)

    def test_empty_list_returns_success(self):
        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"events": []})

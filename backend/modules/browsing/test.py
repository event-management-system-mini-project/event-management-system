
from datetime import timedelta
import uuid

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
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

        past_event = self.create_event(
            "Past",
            today + timedelta(days=1),
            "12:00:00",
        )

        # Simulate an existing record that is now in the past.
        Event.objects.filter(pk=past_event.pk).update(
            date=today - timedelta(days=1)
        )

        self.create_event(
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

    def test_event_details_returns_registration_count_without_personal_data(self):
        event = self.create_event(
            "Details event",
            timezone.localdate() + timedelta(days=2),
            "10:00:00",
        )

        Registration.objects.create(
            event=event,
            name="Synthetic Attendee",
            email="synthetic@example.com",
        )

        response = self.client.get(f"/api/events/{event.id}")

        self.assertEqual(response.status_code, 200)

        item = response.json()["event"]
        self.assertEqual(item["id"], str(event.id))
        self.assertEqual(item["name"], "Details event")
        self.assertEqual(item["registration_count"], 1)
        self.assertNotIn("email", item)
        self.assertNotIn("registrants", item)

    def test_event_details_returns_404_for_unknown_event(self):
        response = self.client.get(f"/api/events/{uuid.uuid4()}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_list_query_count_stays_bounded_as_event_count_grows(self):
        today = timezone.localdate()

        # Measure queries for a small synthetic dataset.
        for index in range(3):
            self.create_event(
                f"Small dataset event {index}",
                today + timedelta(days=index + 1),
                "10:00:00",
            )

        with CaptureQueriesContext(connection) as small_queries:
            small_response = self.client.get("/api/events")

        self.assertEqual(small_response.status_code, 200)
        small_query_count = len(small_queries)

        # Add more events and repeat the measurement.
        for index in range(20):
            self.create_event(
                f"Larger dataset event {index}",
                today + timedelta(days=index + 1),
                "11:00:00",
            )

        with CaptureQueriesContext(connection) as large_queries:
            large_response = self.client.get("/api/events")

        self.assertEqual(large_response.status_code, 200)
        self.assertEqual(len(large_response.json()["events"]), 23)

        large_query_count = len(large_queries)

        # Query count should not grow once per event.
        self.assertLessEqual(
            large_query_count,
            small_query_count + 1,
            msg=(
                f"Possible N+1 query issue: small dataset used "
                f"{small_query_count} queries; larger dataset used "
                f"{large_query_count} queries."
            ),
        )

    def test_event_details_query_count_stays_bounded_with_registrations(self):
        event = self.create_event(
            "Performance detail event",
            timezone.localdate() + timedelta(days=2),
            "10:00:00",
        )

        for index in range(10):
            Registration.objects.create(
                event=event,
                name=f"Synthetic Attendee {index}",
                email=f"synthetic{index}@example.com",
            )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(f"/api/events/{event.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["event"]["registration_count"], 10)

        # Details should not require a query for every registration.
        self.assertLessEqual(
            len(queries),
            5,
            msg=(
                f"Event details used {len(queries)} database queries; "
                "expected no more than 5."
            ),
        )

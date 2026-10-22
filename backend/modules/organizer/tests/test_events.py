"""Event creation, boundaries, ownership and failure behavior."""

import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.db import OperationalError, connection
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.utils import timezone

from events.models import Event
from modules.organizer.event_views import create_event, event_store

from .support import event_payload, make_organizer


class FakeStore:
    def __init__(self):
        self.created = []
        self.listed = []

    def create(self, **kwargs):
        self.created.append(kwargs)
        raise AssertionError("Denied requests must not reach the repository.")

    def for_organizer(self, organizer):
        self.listed.append(organizer)
        return []


class EventCreationTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.other = make_organizer("other-organizer")
        self.client.force_login(self.organizer)

    def post(self, payload):
        return self.client.post(
            "/api/events", data=json.dumps(payload), content_type="application/json"
        )

    def test_valid_event_is_committed_to_the_authenticated_organizer(self):
        response = self.post(event_payload(name="  Synthetic Workshop  "))
        self.assertEqual(response.status_code, 201)
        event = Event.objects.get(pk=response.json()["event"]["id"])
        self.assertEqual(event.organizer_id, self.organizer.id)
        self.assertEqual(event.name, "Synthetic Workshop")
        self.assertEqual(response.json()["event"]["registration_count"], 0)
        self.assertEqual(
            response.json()["event"]["time"], "10:00:00"
        )

    def test_length_and_required_boundaries(self):
        cases = [
            ({"name": "A" * 100}, 201, None),
            ({"name": "A" * 101}, 400, "name"),
            ({"name": "   "}, 400, "name"),
            ({"description": "B" * 1000}, 201, None),
            ({"description": "B" * 1001}, 400, "description"),
            ({"description": ""}, 400, "description"),
            ({"location": "  "}, 400, "location"),
        ]
        for changes, status, field in cases:
            with self.subTest(changes=changes, status=status):
                response = self.post(event_payload(**changes))
                self.assertEqual(response.status_code, status)
                if field:
                    self.assertIn(field, response.json()["error"]["fields"])

    def test_past_and_malformed_date_time_are_rejected(self):
        past = timezone.localtime() - timedelta(minutes=5)
        cases = [
            ({"date": past.date().isoformat(), "time": past.strftime("%H:%M")}, "date"),
            ({"date": "not-a-date"}, "date"),
            ({"time": "25:99"}, "time"),
        ]
        for changes, field in cases:
            with self.subTest(changes=changes):
                response = self.post(event_payload(**changes))
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json()["error"]["fields"])

    def test_client_supplied_organizer_id_cannot_choose_the_owner(self):
        response = self.post(
            event_payload(organizer_id=str(self.other.id), organizer=str(self.other.id))
        )
        self.assertEqual(response.status_code, 201)
        event = Event.objects.get(pk=response.json()["event"]["id"])
        self.assertEqual(event.organizer_id, self.organizer.id)

    def test_server_side_identity_wins_even_when_header_is_spoofed(self):
        response = self.client.post(
            "/api/events",
            data=json.dumps(event_payload()),
            content_type="application/json",
            HTTP_X_ORGANIZER_ID=str(self.other.id),
        )
        self.assertEqual(response.status_code, 201)
        event = Event.objects.get(pk=response.json()["event"]["id"])
        self.assertEqual(event.organizer_id, self.organizer.id)

    def test_organizer_list_contains_only_own_events_ascending(self):
        later = self.post(
            event_payload(
                name="Later Event",
                date=(timezone.localdate() + timedelta(days=40)).isoformat(),
            )
        )
        sooner = self.post(
            event_payload(
                name="Sooner Event",
                date=(timezone.localdate() + timedelta(days=20)).isoformat(),
            )
        )
        self.assertEqual(later.status_code, 201)
        self.assertEqual(sooner.status_code, 201)
        Event.objects.create(
            organizer=self.other,
            name="Other organizer event",
            description="Synthetic",
            date=timezone.localdate() + timedelta(days=5),
            time="09:00:00",
            location="Elsewhere",
        )

        response = self.client.get("/api/organizer/events")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [event["name"] for event in response.json()["events"]],
            ["Sooner Event", "Later Event"],
        )

    def test_database_failure_returns_a_clear_failure_and_no_event(self):
        with patch.object(
            event_store, "create", side_effect=OperationalError("private sql detail")
        ):
            response = self.post(event_payload())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "database_unavailable")
        self.assertNotIn(b"private sql detail", response.content)
        self.assertEqual(Event.objects.count(), 0)

    def test_missing_authentication_is_denied_before_the_repository(self):
        store = FakeStore()
        request = RequestFactory().post(
            "/api/events",
            data=json.dumps(event_payload()),
            content_type="application/json",
        )
        request.user = AnonymousUser()
        with patch("modules.organizer.event_views.event_store", store):
            response = create_event(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["error"]["code"], "authentication_required")
        self.assertEqual(store.created, [])

    def test_unauthenticated_list_is_denied_before_the_repository(self):
        store = FakeStore()
        request = RequestFactory().get("/api/organizer/events")
        request.user = AnonymousUser()
        with patch("modules.organizer.event_views.event_store", store):
            from modules.organizer.event_views import list_own_events

            response = list_own_events(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(store.listed, [])


class CommitFailureTests(TransactionTestCase):
    def setUp(self):
        self.organizer = make_organizer()

    def test_commit_failure_never_returns_created_event(self):
        request = RequestFactory().post(
            "/api/events",
            data=json.dumps(event_payload()),
            content_type="application/json",
        )
        request.user = self.organizer
        results = []
        with patch.object(connection, "_commit", side_effect=OperationalError("commit failed")):
            results.append(create_event(request))
        self.assertEqual(results[0].status_code, 503)
        self.assertEqual(Event.objects.count(), 0)

    def test_csrf_protects_event_creation(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.organizer)
        response = client.post(
            "/api/events",
            data=json.dumps(event_payload()),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")
        self.assertEqual(Event.objects.count(), 0)

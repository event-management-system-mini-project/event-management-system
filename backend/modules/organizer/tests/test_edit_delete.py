"""Owner edit/delete behavior, denial timing and failure rollback."""

import json
import time
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.db import OperationalError, connection
from django.test import Client, RequestFactory, TestCase, TransactionTestCase
from django.utils import timezone

from events.models import Event, Registration
from modules.organizer.event_views import delete_event, event_store, update_event

from .support import event_payload, make_event, make_organizer, make_registration


class OwnerEditTests(TestCase):
    def setUp(self):
        self.owner = make_organizer()
        self.other = make_organizer("other-organizer")
        self.event = make_event(self.owner, name="Original Event")
        self.registration = make_registration(self.event)
        self.client.force_login(self.owner)

    def put(self, payload, event_id=None):
        return self.client.put(
            f"/api/events/{event_id or self.event.id}",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def assert_original_unchanged(self):
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, "Original Event")
        self.assertEqual(self.event.description, event_payload()["description"])
        self.assertEqual(self.event.location, "Synthetic Hall")
        self.assertEqual(
            Registration.objects.filter(event=self.event).count(), 1
        )

    def test_owner_update_is_persisted_and_returns_standard_event(self):
        response = self.put(
            event_payload(
                name="Updated Event",
                description="Updated synthetic description.",
                date=(timezone.localdate() + timedelta(days=60)).isoformat(),
                time="14:30",
                location="Updated Hall",
            )
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["event"]
        self.assertEqual(body["name"], "Updated Event")
        self.assertEqual(body["time"], "14:30:00")
        self.assertEqual(body["location"], "Updated Hall")
        self.assertEqual(body["registration_count"], 1)

        self.event.refresh_from_db()
        self.assertEqual(self.event.name, "Updated Event")
        self.assertEqual(self.event.time.strftime("%H:%M"), "14:30")

    def test_validation_errors_leave_the_original_row_unchanged(self):
        past = timezone.localtime() - timedelta(minutes=5)
        cases = [
            ({"name": "A" * 101}, "name"),
            ({"name": "  "}, "name"),
            ({"description": "B" * 1001}, "description"),
            ({"description": ""}, "description"),
            ({"location": "   "}, "location"),
            ({"date": past.date().isoformat(), "time": past.strftime("%H:%M")}, "date"),
            ({"date": "not-a-date"}, "date"),
            ({"time": "99:99"}, "time"),
        ]
        for changes, field in cases:
            with self.subTest(changes=changes):
                response = self.put(event_payload(**changes))
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json()["error"]["fields"])
                self.assert_original_unchanged()

    def test_client_supplied_owner_cannot_change_ownership(self):
        response = self.put(
            event_payload(
                name="Owner Still Same",
                organizer_id=str(self.other.id),
                organizer=str(self.other.id),
            )
        )
        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.organizer_id, self.owner.id)

    def test_nonowner_edit_is_denied_within_one_second_and_changes_nothing(self):
        self.client.force_login(self.other)
        started = time.perf_counter()
        response = self.put(event_payload(name="Hijacked"))
        elapsed = time.perf_counter() - started

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")
        self.assertLess(elapsed, 1.0)
        print(f"nonowner edit denial: {elapsed * 1000:.1f} ms")
        self.assert_original_unchanged()

    def test_anonymous_edit_is_denied_within_one_second_and_changes_nothing(self):
        self.client.logout()
        started = time.perf_counter()
        response = self.put(event_payload(name="Anonymous change"))
        elapsed = time.perf_counter() - started

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "authentication_required")
        self.assertLess(elapsed, 1.0)
        print(f"anonymous edit denial: {elapsed * 1000:.1f} ms")
        self.assert_original_unchanged()

    def test_missing_event_returns_404(self):
        response = self.put(event_payload(), event_id=uuid4())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_edit_requires_csrf_and_accepts_a_valid_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        denied = client.put(
            f"/api/events/{self.event.id}",
            data=json.dumps(event_payload(name="No Token")),
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["error"]["code"], "csrf_failed")

        client.get("/api/auth/session")
        token = client.cookies["csrftoken"].value
        allowed = client.put(
            f"/api/events/{self.event.id}",
            data=json.dumps(event_payload(name="With Token")),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(allowed.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, "With Token")

    def test_database_failure_leaves_the_original_row_unchanged(self):
        with patch.object(
            event_store, "update", side_effect=OperationalError("private sql detail")
        ):
            response = self.put(event_payload(name="Should Not Persist"))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"private sql detail", response.content)
        self.assert_original_unchanged()


class OwnerDeleteTests(TestCase):
    def setUp(self):
        self.owner = make_organizer()
        self.other = make_organizer("other-organizer")
        self.event = make_event(self.owner, name="Delete Me")
        self.registration = make_registration(self.event)
        self.other_event = make_event(
            self.owner, name="Keep Me", date=(timezone.localdate() + timedelta(days=40)).isoformat()
        )
        self.other_registration = make_registration(
            self.other_event, email="keep@example.com"
        )
        self.client.force_login(self.owner)

    def delete(self, event_id=None):
        return self.client.delete(f"/api/events/{event_id or self.event.id}")

    def assert_rows_preserved(self):
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())
        self.assertTrue(
            Registration.objects.filter(pk=self.registration.pk).exists()
        )
        self.assertTrue(Event.objects.filter(pk=self.other_event.pk).exists())
        self.assertTrue(
            Registration.objects.filter(pk=self.other_registration.pk).exists()
        )

    def test_owner_delete_removes_only_the_event_and_its_registrations(self):
        response = self.delete()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"deleted": True, "event_id": str(self.event.id)}
        )
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())
        self.assertFalse(
            Registration.objects.filter(pk=self.registration.pk).exists()
        )
        self.assertTrue(Event.objects.filter(pk=self.other_event.pk).exists())
        self.assertTrue(
            Registration.objects.filter(pk=self.other_registration.pk).exists()
        )

    def test_nonowner_delete_is_denied_within_one_second_and_changes_nothing(self):
        self.client.force_login(self.other)
        started = time.perf_counter()
        response = self.delete()
        elapsed = time.perf_counter() - started

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "forbidden")
        self.assertLess(elapsed, 1.0)
        print(f"nonowner delete denial: {elapsed * 1000:.1f} ms")
        self.assert_rows_preserved()

    def test_anonymous_delete_is_denied_within_one_second_and_changes_nothing(self):
        self.client.logout()
        started = time.perf_counter()
        response = self.delete()
        elapsed = time.perf_counter() - started

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "authentication_required")
        self.assertLess(elapsed, 1.0)
        print(f"anonymous delete denial: {elapsed * 1000:.1f} ms")
        self.assert_rows_preserved()

    def test_spoofed_identity_header_does_not_authorize_a_nonowner(self):
        self.client.force_login(self.other)
        response = self.client.delete(
            f"/api/events/{self.event.id}",
            HTTP_X_ORGANIZER_ID=str(self.owner.id),
        )
        self.assertEqual(response.status_code, 403)
        self.assert_rows_preserved()

    def test_missing_event_returns_404(self):
        response = self.delete(event_id=uuid4())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_deleted_identifier_is_not_found_on_a_later_get(self):
        deleted_id = self.event.id
        self.assertEqual(self.delete().status_code, 200)
        self.assertFalse(Event.objects.filter(pk=deleted_id).exists())
        response = self.client.get(f"/api/events/{deleted_id}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_delete_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.delete(f"/api/events/{self.event.id}")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")
        self.assert_rows_preserved()

    def test_database_failure_preserves_event_and_registrations(self):
        with patch.object(
            event_store, "delete", side_effect=OperationalError("private sql detail")
        ):
            response = self.delete()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"private sql detail", response.content)
        self.assert_rows_preserved()


class EditDeleteCommitFailureTests(TransactionTestCase):
    def setUp(self):
        self.owner = make_organizer()
        self.event = make_event(self.owner, name="Commit Failure Event")
        self.registration = make_registration(self.event)

    def request(self, method):
        if method == "PUT":
            request = RequestFactory().put(
                f"/api/events/{self.event.id}",
                data=json.dumps(event_payload(name="Uncommitted Edit")),
                content_type="application/json",
            )
        else:
            request = RequestFactory().delete(f"/api/events/{self.event.id}")
        request.user = self.owner
        return request

    def test_update_commit_failure_returns_503_and_rolls_back(self):
        with patch.object(
            connection, "_commit", side_effect=OperationalError("commit failed")
        ):
            response = update_event(self.request("PUT"), self.event.id)
        self.assertEqual(response.status_code, 503)
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, "Commit Failure Event")
        self.assertEqual(
            Registration.objects.filter(event=self.event).count(), 1
        )

    def test_delete_commit_failure_returns_503_and_rolls_back(self):
        with patch.object(
            connection, "_commit", side_effect=OperationalError("commit failed")
        ):
            response = delete_event(self.request("DELETE"), self.event.id)
        self.assertEqual(response.status_code, 503)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())
        self.assertTrue(
            Registration.objects.filter(pk=self.registration.pk).exists()
        )

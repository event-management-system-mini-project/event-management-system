import json
import os
from contextlib import redirect_stdout
from datetime import timedelta
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, OperationalError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from events.auth import AuthenticationRequired, authenticated_organizer
from events.models import Event, Organizer, Registration
from events.repositories import DjangoEventStore, DjangoRegistrationStore, committed_write


def event_fields(**changes):
    fields = {
        "name": "Synthetic Event", "description": "Synthetic description",
        "date": timezone.localdate() + timedelta(days=30),
        "time": "10:00:00", "location": "Synthetic Hall",
    }
    fields.update(changes)
    return fields


class ModelTests(TestCase):
    def setUp(self):
        self.organizer = Organizer.objects.create(username="synthetic-owner", password="!")
        self.event = Event.objects.create(organizer=self.organizer, **event_fields())

    def test_event_length_boundaries(self):
        event = Event.objects.create(
            organizer=self.organizer, **event_fields(name="A" * 100, description="B" * 1000)
        )
        self.assertEqual(len(event.name), 100)
        for fields in [
            {"name": ""}, {"name": "   "}, {"name": "A" * 101},
            {"description": ""}, {"description": "B" * 1001},
            {"location": ""}, {"location": "  "},
        ]:
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                Event.objects.create(organizer=self.organizer, **event_fields(**fields))

    def test_past_event_is_rejected(self):
        past = timezone.localtime() - timedelta(minutes=1)
        with self.assertRaisesMessage(ValidationError, "future"):
            Event.objects.create(
                organizer=self.organizer, **event_fields(date=past.date(), time=past.time())
            )

    def test_name_and_location_are_trimmed(self):
        event = Event.objects.create(
            organizer=self.organizer, **event_fields(name=" Example ", location=" Hall ")
        )
        self.assertEqual((event.name, event.location), ("Example", "Hall"))

    def test_database_checks_reject_bypassing_model_validation(self):
        for changes in [{"name": ""}, {"name": "A" * 101}, {"description": "B" * 1001}]:
            with self.subTest(changes=changes):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Event.objects.bulk_create([
                        Event(organizer=self.organizer, **event_fields(**changes))
                    ])

    def test_registration_validation_and_normalization(self):
        registration = Registration.objects.create(
            event=self.event, name=" Synthetic Attendee ", email=" Student@Example.COM "
        )
        self.assertEqual(registration.name, "Synthetic Attendee")
        self.assertEqual(registration.normalized_email, "student@example.com")
        for name, email in [("", "x@example.com"), ("A" * 101, "x@example.com"), ("A", "invalid")]:
            with self.subTest(name=name, email=email), self.assertRaises(ValidationError):
                Registration.objects.create(event=self.event, name=name, email=email)

    def test_duplicate_constraint_protects_bulk_inserts(self):
        Registration.objects.create(event=self.event, name="A", email="Student@Example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Registration.objects.bulk_create([
                Registration(event=self.event, name="B", email=" student@EXAMPLE.COM ")
            ])
        self.assertEqual(self.event.registrations.count(), 1)

    def test_same_email_can_register_for_different_events(self):
        other = Event.objects.create(organizer=self.organizer, **event_fields(name="Other"))
        for event in [self.event, other]:
            Registration.objects.create(event=event, name="Synthetic", email="a@example.com")
        self.assertEqual(Registration.objects.count(), 2)

    def test_generated_email_stays_normalized_after_update(self):
        registration = Registration.objects.create(
            event=self.event, name="Synthetic", email="before@example.com"
        )
        Registration.objects.filter(pk=registration.pk).update(email=" AFTER@Example.COM ")
        registration.refresh_from_db()
        self.assertEqual(registration.normalized_email, "after@example.com")

    def test_relationships_protect_organizer_and_cascade_explicit_event_delete(self):
        Registration.objects.create(event=self.event, name="Synthetic", email="a@example.com")
        with self.assertRaises(ProtectedError):
            self.organizer.delete()
        self.event.delete()
        self.assertEqual(Registration.objects.count(), 0)
        self.assertTrue(Organizer.objects.filter(pk=self.organizer.pk).exists())


class InterfaceTests(TestCase):
    def test_anonymous_or_spoofed_identity_is_rejected(self):
        request = RequestFactory().get("/api/events", HTTP_X_ORGANIZER_ID="spoofed")
        request.user = AnonymousUser()
        with self.assertRaises(AuthenticationRequired):
            authenticated_organizer(request)

    def test_verified_user_is_used_and_inactive_user_is_rejected(self):
        user = Organizer.objects.create(username="verified", password="!")
        request = RequestFactory().get("/")
        request.user = user
        self.assertEqual(authenticated_organizer(request), user)
        user.is_active = False
        with self.assertRaises(AuthenticationRequired):
            authenticated_organizer(request)

    def test_database_health_and_safe_not_found(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "ok")
        response = self.client.get("/api/events")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_database_failure_does_not_leak_internal_details(self):
        with patch("events.http.connection.cursor", side_effect=OperationalError("private SQL")):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"private SQL", response.content)

    def test_health_is_read_only(self):
        self.assertEqual(self.client.post("/api/health").status_code, 405)

    @override_settings(
        DEBUG=True,
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    )
    def test_demo_data_is_synthetic_future_dated_and_idempotent(self):
        with patch.dict(os.environ, {"EMS_DEMO_PASSWORD": "synthetic-test-password"}):
            with redirect_stdout(StringIO()):
                call_command("seed_demo")
                call_command("seed_demo")
        self.assertEqual(Organizer.objects.count(), 2)
        self.assertEqual(Event.objects.count(), 2)
        self.assertEqual(Registration.objects.count(), 1)
        for event in Event.objects.all():
            self.assertGreater(event.date, timezone.localdate())
        self.assertTrue(Organizer.objects.first().check_password("synthetic-test-password"))

    @override_settings(DEBUG=False)
    def test_demo_seed_is_disabled_outside_development(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo")


class TransactionTests(TransactionTestCase):
    def setUp(self):
        self.owner = Organizer.objects.create(username="owner", password="!")
        self.events = DjangoEventStore()
        self.registrations = DjangoRegistrationStore()

    def test_success_is_returned_after_commit(self):
        event = self.events.create(organizer=self.owner, **event_fields())
        self.assertFalse(connection.in_atomic_block)
        connection.close()
        self.assertTrue(Event.objects.filter(pk=event.pk).exists())
        registration = self.registrations.create(
            event=event, name="Synthetic", email="student@example.com"
        )
        self.assertFalse(connection.in_atomic_block)
        self.assertTrue(Registration.objects.filter(pk=registration.pk).exists())

    def test_exception_after_writes_rolls_back_both_records(self):
        def failing_operation():
            event = Event.objects.create(organizer=self.owner, **event_fields())
            Registration.objects.create(event=event, name="Synthetic", email="s@example.com")
            raise RuntimeError("simulated failure after writes")

        with self.assertRaises(RuntimeError):
            committed_write(failing_operation)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Registration.objects.count(), 0)

    def test_event_commit_failure_returns_no_result_and_rolls_back(self):
        results = []
        with patch.object(connection, "_commit", side_effect=OperationalError("commit failed")):
            with self.assertRaises(OperationalError):
                results.append(self.events.create(organizer=self.owner, **event_fields()))
        self.assertEqual(results, [])
        self.assertEqual(Event.objects.count(), 0)

    def test_registration_commit_failure_leaves_existing_event_intact(self):
        event = self.events.create(organizer=self.owner, **event_fields())
        results = []
        with patch.object(connection, "_commit", side_effect=OperationalError("commit failed")):
            with self.assertRaises(OperationalError):
                results.append(self.registrations.create(
                    event=event, name="Synthetic", email="s@example.com"
                ))
        self.assertEqual(results, [])
        self.assertTrue(Event.objects.filter(pk=event.pk).exists())
        self.assertEqual(Registration.objects.count(), 0)

    def test_nested_transaction_cannot_acknowledge_uncommitted_data(self):
        with transaction.atomic():
            with self.assertRaises(RuntimeError):
                self.events.create(organizer=self.owner, **event_fields())
        self.assertEqual(Event.objects.count(), 0)

    def test_event_store_does_not_accept_client_supplied_owner_override(self):
        with self.assertRaises(TypeError):
            self.events.create(
                organizer=self.owner, organizer_id=self.owner.pk, **event_fields()
            )
        self.assertEqual(Event.objects.count(), 0)

    def test_database_connection_enables_foreign_keys_and_full_sync(self):
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys")
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute("PRAGMA synchronous")
            self.assertEqual(cursor.fetchone()[0], 2)

    def test_foreign_key_rejects_an_orphan_registration(self):
        import uuid
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Registration.objects.bulk_create([
                    Registration(event_id=uuid.uuid4(), name="Synthetic", email="s@example.com")
                ])
        self.assertEqual(Registration.objects.count(), 0)


class RestartTests(TransactionTestCase):
    def test_committed_data_survives_process_exit_and_uncommitted_crash_rolls_back(self):
        root = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory(prefix="ems-restart-") as temporary:
            env = {
                **os.environ, "EMS_DB_PATH": str(Path(temporary) / "restart.sqlite3"),
                "EMS_DEBUG": "1", "DJANGO_SETTINGS_MODULE": "config.settings",
                "PYTHONPATH": str(root / "backend"),
            }

            def run(code, expected=0):
                result = subprocess.run(
                    [sys.executable, "-c", "import django; django.setup();\n" + code],
                    cwd=root, env=env, capture_output=True, text=True, timeout=45,
                    **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}),
                )
                self.assertEqual(result.returncode, expected, result.stderr)
                return result.stdout

            run("from django.core.management import call_command; call_command('migrate', verbosity=0)")
            run(
                "from datetime import timedelta\n"
                "from django.utils import timezone\n"
                "from events.models import Organizer\n"
                "from events.repositories import DjangoEventStore, DjangoRegistrationStore\n"
                "owner=Organizer.objects.create(username='restart-owner',password='!')\n"
                "event=DjangoEventStore().create(organizer=owner,name='Committed',"
                "description='Synthetic',date=timezone.localdate()+timedelta(days=30),"
                "time='10:00:00',location='Demo')\n"
                "DjangoRegistrationStore().create(event=event,name='Synthetic',email='s@example.com')"
            )
            reader = (
                "import json\nfrom events.models import Event, Registration\n"
                "print(json.dumps([Event.objects.count(),Registration.objects.count()]))"
            )
            self.assertEqual(json.loads(run(reader)), [1, 1])
            crash = run(
                "import os\nfrom django.db import transaction\n"
                "from events.models import Event\n"
                "with transaction.atomic():\n"
                "    original=Event.objects.first()\n"
                "    original.pk=None\n"
                "    original.name='Uncommitted'\n"
                "    original.save()\n"
                "    os._exit(17)\n"
                "print('SUCCESS')",
                expected=17,
            )
            self.assertNotIn("SUCCESS", crash)
            self.assertEqual(json.loads(run(reader)), [1, 1])

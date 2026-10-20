import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from events.models import Event, Organizer, Registration

ORGANIZER_A = uuid.UUID("00000000-0000-4000-8000-000000000001")
ORGANIZER_B = uuid.UUID("00000000-0000-4000-8000-000000000002")
EVENT_A = uuid.UUID("10000000-0000-4000-8000-000000000001")
EVENT_B = uuid.UUID("10000000-0000-4000-8000-000000000002")
REGISTRATION_A = uuid.UUID("20000000-0000-4000-8000-000000000001")


class Command(BaseCommand):
    help = "Create idempotent synthetic local-development records (DEBUG only)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo seeding is disabled when EMS_DEBUG is not 1.")
        password = os.getenv("EMS_DEMO_PASSWORD", "")
        if len(password) < 12:
            raise CommandError("Set EMS_DEMO_PASSWORD to a local password of at least 12 characters.")
        with transaction.atomic():
            organizers = []
            for pk, suffix in [(ORGANIZER_A, "a"), (ORGANIZER_B, "b")]:
                organizer, created = Organizer.objects.get_or_create(
                    pk=pk,
                    defaults={
                        "username": f"demo-organizer-{suffix}",
                        "email": f"organizer-{suffix}@example.com",
                    },
                )
                if created:
                    organizer.set_password(password)
                    organizer.save(update_fields=["password"])
                organizers.append(organizer)
            for pk, owner, title, days in [
                (EVENT_A, organizers[0], "Synthetic Tech Workshop", 30),
                (EVENT_B, organizers[1], "Synthetic Community Meetup", 45),
            ]:
                Event.objects.get_or_create(
                    pk=pk,
                    defaults={
                        "organizer": owner, "name": title,
                        "description": "Synthetic local-development event.",
                        "date": (timezone.localdate() + timedelta(days=days)),
                        "time": "10:00:00", "location": "Demo Hall",
                    },
                )
            Registration.objects.get_or_create(
                pk=REGISTRATION_A,
                defaults={
                    "event_id": EVENT_A,
                    "name": "Synthetic Attendee", "email": "attendee@example.com",
                },
            )
        self.stdout.write(
            "Synthetic fixtures ready: demo-organizer-a, demo-organizer-b. "
            "The local password is in EMS_DEMO_PASSWORD; it is not logged."
        )

"""Synthetic, test-only fixtures for the organizer module.

Nothing in this package is imported by production handlers. The helper creates
organizer credentials and logs a test client in through Django's real session
backend; there is no development identity header or bypass endpoint.
"""

import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from events.models import Event, Registration

PASSWORD = "synthetic-organizer-password"


def make_organizer(username="fixture-organizer", *, active=True, **changes):
    return get_user_model().objects.create_user(
        username=username,
        password=PASSWORD,
        is_active=active,
        **changes,
    )


def event_payload(**changes):
    payload = {
        "name": "Synthetic Workshop",
        "description": "Synthetic organizer event for local tests.",
        "date": (timezone.localdate() + timedelta(days=30)).isoformat(),
        "time": "10:00",
        "location": "Synthetic Hall",
    }
    payload.update(changes)
    return payload


def json_body(payload):
    return json.dumps(payload)


def make_event(organizer, **changes):
    return Event.objects.create(organizer=organizer, **event_payload(**changes))


def make_registration(event, name="Synthetic Attendee", email="attendee@example.com"):
    return Registration.objects.create(event=event, name=name, email=email)

from collections.abc import Callable
from typing import TypeVar

from django.db import transaction

from .models import Event, Registration

T = TypeVar("T")


def committed_write(operation: Callable[[], T]) -> T:
    """Return a result only after the outer database commit has succeeded.

    Do not wrap this in another atomic block or enable ATOMIC_REQUESTS: a
    successful inner savepoint is not a durable acknowledgement.
    """
    with transaction.atomic(durable=True):
        result = operation()
    return result


class DjangoEventStore:
    def get(self, event_id):
        return Event.objects.get(pk=event_id)

    def all(self):
        return list(Event.objects.all())

    def create(self, *, organizer, name, description, date, time, location):
        return committed_write(lambda: Event.objects.create(
            organizer=organizer, name=name, description=description,
            date=date, time=time, location=location,
        ))


class DjangoRegistrationStore:
    def for_event(self, event_id):
        return list(Registration.objects.filter(event_id=event_id).order_by("created_at", "id"))

    def create(self, *, event, name, email):
        return committed_write(
            lambda: Registration.objects.create(event=event, name=name, email=email)
        )

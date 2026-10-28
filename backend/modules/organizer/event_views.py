"""Protected organizer event mutations and the organizer's own event list."""

from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import JsonResponse

from events.http import error_response
from events.models import Event
from events.repositories import DjangoEventStore

from .forms import EventForm
from .http import (
    RequestBodyError,
    form_error_response,
    invalid_json_response,
    parse_json,
    require_methods,
)
from .permissions import organizer_required
from .presenters import event_to_json

# The canonical Django/SQLite adapter. Tests may replace this module-level
# instance with a recording fixture; production always uses the real adapter.
event_store = DjangoEventStore()


def _owned_event(request, event_id):
    """Return the event only when the verified organizer owns it."""
    try:
        event = event_store.get(event_id)
    except Event.DoesNotExist:
        return None, error_response(
            "not_found", "The requested event does not exist.", 404
        )
    except DatabaseError:
        return None, error_response(
            "database_unavailable", "The event could not be loaded.", 503
        )
    if event.organizer_id != request.organizer.id:
        return None, error_response(
            "forbidden",
            "Only the event owner can change this event.",
            403,
        )
    return event, None


@require_methods("POST")
@organizer_required
def create_event(request):
    try:
        payload = parse_json(request)
    except RequestBodyError as error:
        return invalid_json_response(error)

    form = EventForm(payload)
    if not form.is_valid():
        return form_error_response(form)

    try:
        # The store returns only after the outermost database commit succeeds.
        event = event_store.create(organizer=request.organizer, **form.cleaned_data)
    except ValidationError as error:
        return error_response(
            "invalid_input",
            "Correct the invalid fields.",
            400,
            fields=getattr(error, "message_dict", None),
        )
    except DatabaseError:
        # Never acknowledge a write whose commit did not complete.
        return error_response(
            "database_unavailable",
            "The event could not be saved. Try again.",
            503,
        )
    return JsonResponse({"event": event_to_json(event)}, status=201)


@require_methods("GET")
@organizer_required
def list_own_events(request):
    try:
        events = event_store.for_organizer(request.organizer)
    except DatabaseError:
        return error_response(
            "database_unavailable",
            "The organizer events could not be loaded.",
            503,
        )
    return JsonResponse({"events": [event_to_json(event) for event in events]})


@require_methods("PUT")
@organizer_required
def update_event(request, event_id):
    """Update an event owned by the verified organizer."""
    event, error = _owned_event(request, event_id)
    if error:
        return error

    try:
        payload = parse_json(request)
    except RequestBodyError as error:
        return invalid_json_response(error)

    form = EventForm(payload)
    if not form.is_valid():
        return form_error_response(form)

    try:
        # The store commits the full update before returning the new state.
        event = event_store.update(event, **form.cleaned_data)
    except ValidationError as error:
        return error_response(
            "invalid_input",
            "Correct the invalid fields.",
            400,
            fields=getattr(error, "message_dict", None),
        )
    except DatabaseError:
        # A failed update leaves the original committed row unchanged.
        return error_response(
            "database_unavailable",
            "The event could not be updated. Try again.",
            503,
        )
    return JsonResponse({"event": event_to_json(event)})


@require_methods("DELETE")
@organizer_required
def delete_event(request, event_id):
    """Delete an owned event and its registrations atomically."""
    event, error = _owned_event(request, event_id)
    if error:
        return error

    deleted_id = event.id
    try:
        event_store.delete(event)
    except DatabaseError:
        # The transaction rolled back; no event or registration was removed.
        return error_response(
            "database_unavailable",
            "The event could not be deleted. Try again.",
            503,
        )
    return JsonResponse({"deleted": True, "event_id": str(deleted_id)})

"""Protected organizer event mutations and the organizer's own event list."""

from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import JsonResponse

from events.http import error_response
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

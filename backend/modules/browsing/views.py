
from django.db import DatabaseError
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone

from events.http import error_response
from events.models import Event


def list_upcoming_events(request):
    if request.method != "GET":
        response = error_response(
            "method_not_allowed",
            "Use GET for this resource.",
            405,
        )
        response["Allow"] = "GET"
        return response

    now = timezone.localtime()
    today = now.date()
    current_time = now.time()

    try:
        events = (
            Event.objects.filter(
                Q(date__gt=today)
                | Q(date=today, time__gt=current_time)
            )
            .annotate(registration_count=Count("registrations"))
            .order_by("date", "time", "id")
        )

        results = [
            {
                "id": str(event.id),
                "name": event.name,
                "description": event.description,
                "date": event.date.isoformat(),
                "time": event.time.isoformat(),
                "location": event.location,
                "registration_count": event.registration_count,
            }
            for event in events
        ]
    except DatabaseError:
        return error_response(
            "unavailable",
            "Events could not be loaded right now.",
            503,
        )

    return JsonResponse({"events": results})

def get_event_details(request, event_id):
    if request.method != "GET":
        response = error_response(
            "method_not_allowed",
            "Use GET for this resource.",
            405,
        )
        response["Allow"] = "GET"
        return response

    try:
        event = (
            Event.objects.filter(id=event_id)
            .annotate(registration_count=Count("registrations"))
            .first()
        )
    except DatabaseError:
        return error_response(
            "unavailable",
            "Event details could not be loaded right now.",
            503,
        )

    if event is None:
        return error_response(
            "not_found",
            "The requested event does not exist.",
            404,
        )

    return JsonResponse({
        "event": {
            "id": str(event.id),
            "name": event.name,
            "description": event.description,
            "date": event.date.isoformat(),
            "time": event.time.isoformat(),
            "location": event.location,
            "registration_count": event.registration_count,
        }
    })
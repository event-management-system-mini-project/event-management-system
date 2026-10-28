from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Event, Registration

# --- Keep existing register_attendee view above ---

@api_view(["GET"])
@permission_classes([AllowAny])
def event_registrations_list(request, event_id):
    """
    GET /api/events/{id}/registrations
    Returns registrant details only if the requester is the verified event owner.
    """
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)

    # Check organizer identity from header or query param
    organizer_id = request.headers.get("X-Organizer-Id") or request.GET.get("organizer_id")

    # Reject non-owner or anonymous requests without exposing data
    if not organizer_id or str(event.organizer_id) != str(organizer_id):
        return Response(
            {"detail": "Unauthorized access. Only the event owner can view registrations."},
            status=status.HTTP_403_FORBIDDEN
        )

    registrations = Registration.objects.filter(event=event).order_by("-created_at")
    registrant_data = [
        {
            "id": str(reg.id),
            "name": reg.name,
            "email": reg.email,
            "created_at": reg.created_at,
        }
        for reg in registrations
    ]

    return Response(
        {
            "event_id": str(event.id),
            "event_title": event.title,
            "registration_count": registrations.count(),
            "registrants": registrant_data,
        },
        status=status.HTTP_200_OK,
    )
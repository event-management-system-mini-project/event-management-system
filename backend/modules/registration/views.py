from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Event, Registration


@api_view(["POST"])
@permission_classes([AllowAny])
def register_attendee(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)

    name = request.data.get("name", "").strip()
    email = request.data.get("email", "").strip()

    if not name or not email:
        return Response(
            {"detail": "Both name and email are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        registration = Registration.objects.create(
            event=event, name=name, email=email
        )
        return Response(
            {
                "id": str(registration.id),
                "name": registration.name,
                "email": registration.email,
                "event": str(event.id),
                "created_at": registration.created_at,
            },
            status=status.HTTP_201_CREATED,
        )
    except IntegrityError:
        # Caught by database unique constraint for atomic duplicate prevention [BL-08]
        return Response(
            {
                "detail": "This email is already registered for this event.",
                "fields": {"email": ["This email is already registered for this event."]},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
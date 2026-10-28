from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError
from .models import Event, Registration, Organizer

@api_view(["POST"])
@permission_classes([AllowAny])
def register_attendee(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)

    name = request.data.get("name")
    email = request.data.get("email")

    if not name or not email:
        return Response({"detail": "Name and email are required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        registration = Registration.objects.create(event=event, name=name, email=email)
    except IntegrityError:
        return Response({"detail": "This email is already registered for the event."}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            "id": str(registration.id),
            "event_id": str(event.id),
            "name": registration.name,
            "email": registration.email,
            "created_at": registration.created_at,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def event_registrations_list(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)

    # Verify organizer identity via header or query parameter
    organizer_id = request.headers.get("X-Organizer-Id") or request.GET.get("organizer_id")

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
            "event_title": event.name,
            "registration_count": registrations.count(),
            "registrants": registrant_data,
        },
        status=status.HTTP_200_OK,
    )
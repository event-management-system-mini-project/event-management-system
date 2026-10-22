"""JSON representations exposed by the organizer module.

Public event payloads contain event details and aggregate counts only. They do
not contain organizer credentials or registrant personal data.
"""


def organizer_to_json(organizer):
    return {"id": str(organizer.id), "username": organizer.username}


def event_to_json(event):
    return {
        "id": str(event.id),
        "name": event.name,
        "description": event.description,
        "date": event.date.isoformat(),
        "time": event.time.strftime("%H:%M:%S"),
        "location": event.location,
        "registration_count": event.registrations.count(),
    }

"""Reuse the platform's verified-identity boundary for protected actions."""

from functools import wraps

from events.auth import AuthenticationRequired, authenticated_organizer
from events.http import error_response


def organizer_required(view):
    """Attach the Django-authenticated organizer or return a JSON 401.

    The decorated handler must read ``request.organizer``. Request bodies,
    headers and query parameters are never accepted as the identity source, so
    the same check protects create, edit and delete handlers.
    """

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            request.organizer = authenticated_organizer(request)
        except AuthenticationRequired:
            return error_response(
                "authentication_required",
                "Organizer authentication is required.",
                401,
            )
        return view(request, *args, **kwargs)

    return wrapped

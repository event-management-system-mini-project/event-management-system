from django.core.exceptions import PermissionDenied


class AuthenticationRequired(PermissionDenied):
    """Map this to a standard 401 JSON response in an API handler."""


def authenticated_organizer(request):
    """Read verified Django identity, never headers, JSON or query parameters."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or not user.is_active:
        raise AuthenticationRequired("Organizer authentication is required.")
    return user

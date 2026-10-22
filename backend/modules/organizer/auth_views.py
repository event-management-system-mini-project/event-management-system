"""Organizer session endpoints built on Django's verified auth/session adapter."""

from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from .forms import LoginForm
from .http import (
    RequestBodyError,
    form_error_response,
    invalid_json_response,
    parse_json,
    require_methods,
)
from .presenters import organizer_to_json
from events.http import error_response


def _current_organizer(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or not user.is_active:
        return None
    return user


@ensure_csrf_cookie
@require_methods("GET")
def session_view(request):
    """Report the verified session and make the CSRF cookie available."""
    organizer = _current_organizer(request)
    return JsonResponse(
        {"organizer": organizer_to_json(organizer) if organizer else None}
    )


@require_methods("POST")
def login_view(request):
    try:
        payload = parse_json(request)
    except RequestBodyError as error:
        return invalid_json_response(error)

    form = LoginForm(payload)
    if not form.is_valid():
        return form_error_response(
            form, message="Enter your username and password."
        )

    organizer = authenticate(
        request,
        username=form.cleaned_data["username"],
        password=form.cleaned_data["password"],
    )
    if organizer is None:
        # The message is deliberately identical for unknown and inactive accounts.
        return error_response(
            "invalid_credentials",
            "The username or password is incorrect.",
            401,
        )

    # Rotate the session identifier on login, then use only the server session.
    django_login(request, organizer)
    return JsonResponse({"organizer": organizer_to_json(organizer)})


@require_methods("POST")
def logout_view(request):
    """End the Django session; repeating logout is harmless."""
    django_logout(request)
    return JsonResponse({"logged_out": True})

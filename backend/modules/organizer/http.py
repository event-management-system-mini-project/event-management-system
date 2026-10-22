"""Small HTTP helpers shared by the organizer API handlers."""

import json
from functools import wraps

from events.http import error_response


class RequestBodyError(ValueError):
    """The submitted JSON body cannot be used as an API payload."""


def parse_json(request):
    """Return the JSON object in the request body, or raise RequestBodyError.

    Request bodies are never logged: they can contain organizer credentials.
    """
    if not request.body:
        return {}
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RequestBodyError("The request body must be valid JSON.") from error
    if not isinstance(payload, dict):
        raise RequestBodyError("The request body must be a JSON object.")
    return payload


def invalid_json_response(error):
    return error_response("invalid_json", str(error), 400)


def form_error_response(form, *, message="Correct the invalid fields.", status=400):
    fields = {
        field: [str(item) for item in errors]
        for field, errors in form.errors.items()
    }
    return error_response("invalid_input", message, status, fields=fields)


def method_not_allowed(allowed):
    """Build a JSON 405 while keeping the HTTP Allow header accurate."""
    response = error_response(
        "method_not_allowed",
        f"Use {', '.join(allowed)} for this resource.",
        405,
    )
    response["Allow"] = ", ".join(allowed)
    return response


def require_methods(*allowed):
    """Reject other methods with the documented JSON error shape."""

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method not in allowed:
                return method_not_allowed(allowed)
            return view(request, *args, **kwargs)

        return wrapped

    return decorator

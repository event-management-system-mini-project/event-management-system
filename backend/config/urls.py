from django.urls import include, path, re_path
from events.http import health, not_found
from modules.organizer.event_views import create_event

# GET /api/events belongs to the browsing module; POST belongs to the organizer
# module. Django resolves URLs by path rather than method, so this collection
# route composes both modules at one integration point. Add GET here when the
# browsing module provides its real handler. Unimplemented methods stay 404,
# matching the documented "not implemented yet" contract.
EVENT_COLLECTION = {"POST": create_event}


def event_collection(request):
    handler = EVENT_COLLECTION.get(request.method)
    if handler is None:
        return not_found(request)
    return handler(request)


urlpatterns = [
    path("api/health", health),
    path("api/events", event_collection),
    path("api/", include("modules.organizer.urls")),
    path("api/", include("modules.browsing.urls")),
    path("api/", include("events.urls")),
    re_path(r"^.*$", not_found),
]
handler400 = "events.http.bad_request"
handler403 = "events.http.forbidden"
handler404 = "events.http.not_found"
handler500 = "events.http.server_error"

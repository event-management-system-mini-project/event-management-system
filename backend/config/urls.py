from django.urls import include, path, re_path
from django.contrib import admin
from events.http import health, not_found
from modules.organizer.event_views import (
    create_event,
    delete_event,
    update_event,
)

from modules.browsing.views import (
    get_event_details,
    list_upcoming_events,
)

# GET /api/events belongs to the browsing module; POST belongs to the organizer
# module. Django resolves URLs by path rather than method, so this collection
# route composes both modules at one integration point. Unsupported methods
# return the standard not-found response.
EVENT_COLLECTION = {
    "GET": list_upcoming_events,
    "POST": create_event,
}


def event_collection(request):
    handler = EVENT_COLLECTION.get(request.method)
    if handler is None:
        return not_found(request)
    return handler(request)


# GET /api/events/{id} belongs to the browsing module. PUT and DELETE belong to
# the organizer module, so the detail route uses the same method dispatch.
EVENT_ITEM = {
    "GET": get_event_details,
    "PUT": update_event,
    "DELETE": delete_event,
}


def event_item(request, event_id):
    handler = EVENT_ITEM.get(request.method)
    if handler is None:
        return not_found(request)
    return handler(request, event_id)


urlpatterns = [
   
    path("api/", include("modules.registrants.urls")),
    path("api/health", health),
    path("api/events", event_collection),
    path("api/events/<uuid:event_id>", event_item),
    path("api/", include("modules.organizer.urls")),
    path("api/", include("modules.browsing.urls")),
 
    path("api/", include("modules.registrants.urls")),
    path("api/", include("events.urls")),

    path("api/", include("modules.registration.urls")),
 
    re_path(r"^.*$", not_found),
]
handler400 = "events.http.bad_request"
handler403 = "events.http.forbidden"
handler404 = "events.http.not_found"

handler500 = "events.http.server_error"

handler500 = "events.http.server_error"



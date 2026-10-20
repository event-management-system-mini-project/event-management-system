from django.urls import include, path, re_path
from events.http import health, not_found

urlpatterns = [
    path("api/health", health),
    path("api/", include("modules.organizer.urls")),
    path("api/", include("modules.browsing.urls")),
    path("api/", include("modules.registration.urls")),
    re_path(r"^.*$", not_found),
]
handler400 = "events.http.bad_request"
handler403 = "events.http.forbidden"
handler404 = "events.http.not_found"
handler500 = "events.http.server_error"

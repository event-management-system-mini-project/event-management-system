from django.db import DatabaseError, connection
from django.http import JsonResponse


def error_response(code, message, status, fields=None):
    error = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return JsonResponse({"error": error}, status=status)


def health(request):
    if request.method != "GET":
        response = error_response("method_not_allowed", "Use GET for this resource.", 405)
        response["Allow"] = "GET"
        return response
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return error_response("unavailable", "The database is unavailable.", 503)
    return JsonResponse({"status": "ok", "service": "django", "database": "ok"})


def not_found(request, exception=None):
    return error_response("not_found", "The requested resource does not exist.", 404)


def bad_request(request, exception=None):
    return error_response("bad_request", "The request could not be processed.", 400)


def forbidden(request, exception=None):
    return error_response("forbidden", "The request is not permitted.", 403)


def server_error(request):
    return error_response("internal_error", "The request could not be completed.", 500)


def csrf_failure(request, reason=""):
    return error_response("csrf_failed", "CSRF verification failed.", 403)

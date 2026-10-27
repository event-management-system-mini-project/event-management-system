# JSON API contract

IDs are opaque UUID strings. Dates use YYYY-MM-DD, times use HH:mm:ss, and event
date/time is interpreted in Asia/Kolkata. All API payloads use JSON.
[Examples](api-examples.json) contain synthetic data only.

The platform implements **GET /api/health** and the organizer module implements
the authentication and event-creation routes below. The remaining feature routes
are the agreed integration contract; they return safe 404 JSON until implemented
in their feature modules. Their presence here is not a claim that the features
are complete.

## Organizer authentication

Django's database-backed session cookie is the auth transport. The browser reads
the `csrftoken` cookie set by `GET /api/auth/session` and sends it as
`X-CSRFToken` on every POST. Login rotates the session and CSRF token.

| Method | Route | Body | Successful response |
| --- | --- | --- | --- |
| GET | /api/auth/session | — | 200, `{organizer: {id, username}}` or `{organizer: null}`; sets CSRF cookie |
| POST | /api/auth/login | `{username, password}` | 200, `{organizer: {id, username}}`; sets session cookie |
| POST | /api/auth/logout | — | 200, `{logged_out: true}`; ends the session |

Unknown accounts, inactive accounts and wrong passwords all return
`401 {error: {code: "invalid_credentials", message: "The username or password is incorrect."}}`.
Login and logout are CSRF-protected. The API never returns a password, session key
or organizer ID taken from the request body or headers.

## Events

| Method | Route | Body | Successful status and response |
| --- | --- | --- | --- |
| GET | /api/health | — | 200, {status: "ok", service: "django", database: "ok"} |
| GET | /api/events | — | 200, {events: [...]} upcoming events, ascending date/time |
| GET | /api/events/{id} | — | 200, {event: {..., registration_count}} |
| POST | /api/events | name, description, date, time, location | 201, {event: {...}} after commit; organizer from verified session |
| GET | /api/organizer/events | — | 200, {events: [...]} only the verified organizer's events |
| PUT | /api/events/{id} | name, description, date, time, location | 200, {event: {...}} |
| DELETE | /api/events/{id} | — | 200, {deleted: true, event_id} |
| POST | /api/events/{id}/registrations | name, email | 201, {registration: {id,event_id}, registration_count} after commit |
| GET | /api/events/{id}/registrations | — | 200, {registrants: [{id,name,email}], registration_count} for the verified owner |

`POST /api/events` requires an authenticated organizer and validates name
(1–100 characters), description (1–1000), location (non-empty) and a future
date/time in Asia/Kolkata. Invalid fields return 400 with a `fields` object.
A database or commit failure returns 503 `database_unavailable` and no event is
reported as created. Any submitted `organizer_id` is ignored; the session identity
always owns the event.

Event date/time fields are interpreted as **Asia/Kolkata (IST, UTC+05:30, no
daylight saving)** by both the React form and the Django server. The form's
minimum date and future check use the IST calendar even when the browser is in
another timezone. A same-day event is accepted only when its entered time is
later than the current IST time; this is the same `starts_at <= now` rule used by
the backend. The form does not fall back to the browser's local timezone.

`PUT` and `DELETE /api/events/{id}` require the verified owner and CSRF. A
different authenticated organizer receives 403 before the body is parsed or the
event is changed. Invalid edits return field errors and leave the original event
and its registrations unchanged; delete removes the event and its registrations in
one committed transaction. A later request for the deleted identifier is not found.

Create/edit bodies contain name, description, date, time and location.
The backend takes organizer identity from verified Django authentication, never
from a submitted organizer_id. Registration bodies contain name and email.
Public event responses contain event information and aggregate counts, not
registrant names/emails or organizer credentials. The registration component may
call `onRegistered({event_id, registration_count})`; the details host then refetches.

## Errors

Use `{error: {code, message, fields?}}`, where optional `fields` maps field names
to arrays of validation messages. Do not expose SQL, exceptions, passwords or sessions.

| Status | Meaning |
| --- | --- |
| 400 | Missing/invalid input |
| 401 | Organizer authentication required |
| 403 | Authenticated user is not the owner, or CSRF verification failed |
| 404 | Missing event/resource |
| 409 | Duplicate event/email registration |
| 500 | Unexpected internal failure |
| 502 | Gateway cannot reach the Django service |
| 503 | Database health check unavailable, or an event write could not be committed |

Django session cookies and CSRF validation are the auth transport baseline.
Login/logout route details belong to the organizer module; the platform's
`authenticated_organizer()` adapter is the stable verified-identity boundary.
No development-only identity header is part of this public API.

API handlers must invoke the committed repository boundary before sending success.
Whole-app response-time checks use the real integrated UI/API/database and record
their environment: list under 2 seconds, details within 2 seconds, registration
confirmation within 3 seconds, nonowner edit/delete denial within 1 second.

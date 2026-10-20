# JSON API contract

IDs are opaque UUID strings. Dates use YYYY-MM-DD, times use HH:mm:ss, and event
date/time is interpreted in Asia/Kolkata. All API payloads use JSON.
[Examples](api-examples.json) contain synthetic data only.

The platform implements **GET /api/health**. The feature routes below are the
agreed integration contract; they return safe 404 JSON until implemented in their
feature modules. Their presence here is not a claim that the features are complete.

| Method | Route | Successful status and response |
| --- | --- | --- |
| GET | /api/health | 200, {status: "ok", service: "django", database: "ok"} |
| GET | /api/events | 200, {events: [...]} upcoming events, ascending date/time |
| GET | /api/events/{id} | 200, {event: {..., registration_count}} |
| POST | /api/events | 201, {event: {...}} after commit |
| PUT | /api/events/{id} | 200, {event: {...}} |
| DELETE | /api/events/{id} | 200, {deleted: true, event_id} |
| POST | /api/events/{id}/registrations | 201, {registration: {id,event_id}, registration_count} after commit |
| GET | /api/events/{id}/registrations | 200, {registrants: [{id,name,email}], registration_count} for the verified owner |

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
| 503 | Database health check unavailable |

Django session cookies and CSRF validation are the auth transport baseline.
Login/logout route details belong to the organizer module; the platform's
`authenticated_organizer()` adapter is the stable verified-identity boundary.
No development-only identity header is part of this public API.

API handlers must invoke the committed repository boundary before sending success.
Whole-app response-time checks use the real integrated UI/API/database and record
their environment: list under 2 seconds, details within 2 seconds, registration
confirmation within 3 seconds, nonowner edit/delete denial within 1 second.

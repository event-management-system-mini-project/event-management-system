# Platform and data decisions

## Architecture

The application keeps the SRS's React + Node.js + Django stack in one repository.
React handles presentation. Node is a thin HTTP API gateway, preserving cookies
and CSRF headers; it does not implement a second copy of event business logic.
Django exposes JSON endpoints and owns authentication, validation and relational
data access. This resolves the backend division left open in SAD section 4.6
without introducing independently deployed microservices.

SQLite is the local database: no separate database server or paid service is
needed. A future hosting/database change must include fresh migration, uniqueness,
transaction and restore checks. This setup does not claim production-scale
availability, throughput or power-loss recovery.

## Canonical data

| Model | Important fields | Relationships |
| --- | --- | --- |
| Organizer | UUID id, username, hashed password, active flag | Django's custom user model |
| Event | UUID id, name, description, date, time, location | Required organizer; deleting an organizer with events is protected |
| Registration | UUID id, name, email, generated normalized_email | Required event; deliberate ORM event deletion removes its registrations |

Names are 1-100 characters; event descriptions are required and at most 1000
characters; location is required. Inputs are trimmed and model saves run
validation. Event date/time must be in the future at write time, interpreted in
**Asia/Kolkata**. Already-stored records may naturally become past events.
Database checks protect required fields and important lengths, including when
ordinary model validation is bypassed. Format and future-time validation still
belong to validated model/repository writes, not unchecked bulk SQL.

Email is trimmed, validated by Django and stored without altering its original
case. SQLite generates `normalized_email = lower(trim(email))` and enforces a
unique `(event_id, normalized_email)` pair. Thus standard ASCII email addresses
are compared case-insensitively for the same event, including bulk inserts and
updates, and the same address can appear on different events. SQLite's
`lower()` is ASCII-oriented; internationalized email case-folding is not claimed.
A new database adapter must preserve and retest this explicit policy.

Event/registration relationships are foreign keys. Intentional event deletion
uses Django ORM cascade inside an explicit transaction; it is distinct from
accidental loss of a confirmed record. Direct SQL deletion is not an API.
Daily backups and their restore procedure are separate sprint work.

## Write acknowledgement

`events.repositories.committed_write()` uses an outermost durable atomic block.
It returns only after commit succeeds; a write/commit exception propagates after
rollback, so an API must send success only after this helper returns.
Nesting it inside another transaction is rejected because releasing a savepoint
is not the same as committing. Keep `ATOMIC_REQUESTS=False`.

`DjangoEventStore` and `DjangoRegistrationStore` are the real database adapters.
Their small protocols are in `events/ports.py`. API handlers add authorization
and translate model/database errors to the documented JSON shape. They must not
send a response, set a success flag, or stream success from inside a pending
transaction. Post-commit side effects, if added later, need their own failure policy.

SQLite connections enable foreign keys and `synchronous=FULL`. Tests prove
process-restart persistence and rollback, not recovery from every hardware or
filesystem failure. Keep the working database on suitable local storage and
do not use the same file concurrently from multiple machines through cloud sync.

## Authentication adapter

Use `events.auth.authenticated_organizer(request)` to obtain the active
Django-authenticated user. The custom Organizer uses Django's password hashing,
session backend, authentication middleware and CSRF middleware. User IDs from
request bodies, URLs or headers never establish identity.
The Node gateway strips identity-spoofing and forwarding headers rather than
trusting them. Login/logout endpoints and event-owner permission checks are
implemented in the organizer module.

Development uses local HTTP and `EMS_DEBUG=1`. Outside development, settings
require a real secret and enable secure cookies and HTTPS redirection; actual
hosting/TLS termination configuration and validation are separate deployment work.
Do not enable proxy-header trust without a trusted TLS proxy and its own checks.

## Module interfaces

Canonical migrations/configuration stay in `backend/events/` and `backend/config/`.
Feature modules register their URLs from their respective `urls.py` files.
Organizer, browsing and registration modules can test their own real handlers
against synthetic repository/identity fixtures, then connect these canonical
adapters during integration. Fixture-only identity providers must never be wired
into production.

References: SRS sections 2.4-2.5, 3.2-3.3, 6.2-6.3 and 7; SAD sections 3.5-3.9 and
4.3-4.6; Test Plan NFR_03, REQ1_IT_02 and REQ4_IT_02.

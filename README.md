# Event Management System

A full-stack event platform built by **Team 7** for the Software Engineering
mini-project. Organizers sign in, create events, and manage only the events they
own. Attendees browse upcoming events and register with their name and email.

React 19 provides the browser interface, a small Node.js gateway forwards
same-origin API traffic, Django owns authentication, validation and data access,
and SQLite stores the data. The submitted SRS, architecture and test-plan
documents remain at the repository root.

## Current status

| Area | State |
| --- | --- |
| Organizer authentication, create, owner-only edit/delete, own event list | Implemented, tested and wired into the React UI |
| Public upcoming-events list (anonymous, ascending date/time) | Implemented, tested and wired into the React UI |
| Event-details API with registration count | Implemented and tested; a detail screen is not yet mounted in the main React view |
| Attendee registration with per-event duplicate-email prevention | Implemented and tested; the database rejects duplicates. `RegistrationForm.jsx` exists but is not yet mounted in the main view |
| Owner-only registrant list | Route implemented; it still needs verified-session integration and tests before SEC-3 sign-off |
| HTTPS deployment, scheduled backups and isolated restore | Docker Compose stack and executable checks provided; real-host acceptance pending |

`docs/final-acceptance.md` tracks the remaining sign-off work. The verified
results quoted below come from `docs/sprint-2-platform-verification.md`; treat
test counts as evidence for that revision, not a permanent guarantee.

## Run locally

Requirements: **Python 3.11+**, **Node.js 22.12+**, and npm. SQLite is included
with Python.

```text
python scripts/bootstrap.py
npm run dev
```

Open **http://127.0.0.1:5173**. The organizer sign-in panel uses the real React
→ Node → Django → SQLite path; the upcoming-events list is public.

Setup creates an ignored `.env` with random local secrets, installs pinned
dependencies, applies migrations and creates synthetic sample records. Existing
secrets and records are preserved when setup is repeated. To reuse already
installed dependencies, run `python scripts/bootstrap.py --skip-install`.

Two synthetic accounts are created: `demo-organizer-a` and `demo-organizer-b`.
Their local password is the value of `EMS_DEMO_PASSWORD` in your ignored `.env`
(`grep EMS_DEMO_PASSWORD .env`). Passwords are hashed in the database and are
never printed by setup. Demo seeding is disabled when `EMS_DEBUG` is not `1`.

Press **Ctrl+C** to stop the three development services. Default addresses:

| Component | Address | Responsibility |
| --- | --- | --- |
| React/Vite | 127.0.0.1:5173 | Browser interface and same-origin development proxy |
| Node.js | 127.0.0.1:3000 | Thin API gateway; forwards bodies, session cookies and CSRF tokens |
| Django | 127.0.0.1:8000 | REST modules, verified authentication, validation and data access |
| SQLite | data/events.sqlite3 | Local relational storage |

Organizer create/edit/delete handlers take identity from the verified Django
session, never from a submitted `organizer_id` or a development identity header.
Event and registration writes report success only after the database commit.

## Check the platform

```text
npm test
npm run check
npm run build
npm run smoke
```

| Command | Scope |
| --- | --- |
| `npm test` | Platform, organizer, registration, gateway and React suites |
| `node scripts/python.mjs backend/manage.py test modules.browsing` | Public upcoming-event and event-detail queries |
| `npm run test:frontend` | React validation, auth, event forms, delete confirmation and shared UI states |
| `npm run build` | Production React bundle |
| `npm run smoke` | Fresh temporary database plus React, gateway and Django services |

The backend suites use a disposable test database. They include a
separate-process file-database test for committed records surviving exit and
pending writes rolling back after abrupt process termination. The React suite is
also run under `TZ=UTC` and `TZ=America/Los_Angeles` in CI because event times
are validated against **Asia/Kolkata (IST, UTC+05:30)** regardless of browser
timezone.

Platform reliability checks that are not part of `npm test`:

```text
python -m unittest discover -s scripts -p test_db_backup.py -v
node scripts/python.mjs scripts/backup_smoke.py
python scripts/deploy_smoke.py
```

The Sprint 2 verification run recorded **122 passing regression tests** across
the Django, gateway, React, browsing and backup suites. See
[testing and review workflow](docs/testing.md) for narrower commands and the
[result-log template](docs/test-results-template.md) for recording new runs.

To check migration consistency:

```text
node scripts/python.mjs backend/manage.py makemigrations --check --dry-run
```

## Deployment

`deploy/compose.yml` runs a built React site behind Caddy (automatic TLS), the
Node gateway, Gunicorn/Django, a persistent SQLite volume and a backup worker.
Only Caddy publishes ports; the API services share a private network.

```text
docker compose --env-file deploy/.env -f deploy/compose.yml up -d --build --wait
```

Follow [deployment and recovery](docs/operations.md) for secrets, DNS/TLS,
health checks, backup retention, restore steps and the single-host SQLite
limitations. Do not commit `deploy/.env`, database files or backup snapshots.

## Project structure

- `backend/events/`: canonical `Organizer`, `Event` and `Registration` models,
  migrations, repository interfaces, committed-write helpers, authentication
  adapter, seeding command and platform tests.
- `backend/modules/organizer/`: organizer session authentication and event
  create/edit/delete with ownership checks.
- `backend/modules/browsing/`: public upcoming-event list and event-details
  queries with aggregate registration counts.
- `backend/modules/registration/`: attendee registration and duplicate-email
  rejection.
- `backend/modules/registrants/`: registrant-listing route; it must move to the
  verified session boundary before it can be treated as owner-only.
- `gateway/`: Node HTTP gateway and forwarding/identity-header tests.
- `frontend/`: React organizer workspace, public event list and shared
  accessible UI states (`LoadingState`, `EmptyState`, `ErrorState`, `FormField`,
  `SharedButton`, `SharedLayout`).
- `deploy/`: Docker Compose stack, Caddy configuration, image definitions and an
  optional platform CI template.
- `scripts/`: bootstrap, development launcher, smoke, browsing benchmark,
  backup/restore and deployment verification scripts.
- `docs/`: API contract, platform decisions, operations, verification evidence
  and acceptance tracking.
- Repository root: SRS, SAD and Test Plan deliverables for the course.

## API and data contracts

IDs are opaque UUID strings. Dates use `YYYY-MM-DD`, times use `HH:mm:ss`, and
event date/time is interpreted in **Asia/Kolkata**. Responses are JSON and
errors use `{error: {code, message, fields?}}`; see the
[API contract](docs/api.md) and [synthetic examples](docs/api-examples.json).

Event names are 1–100 characters, descriptions are required and at most 1000
characters, locations are required, and event date/time must be in the future at
write time. Email comparison is case-insensitive per event through a generated
`normalized_email` column and a unique `(event_id, normalized_email)` constraint.
Organizer deletion is protected while events exist; intentional event deletion
cascades to its registrations inside a committed transaction.

## Documentation

- [Platform and data decisions](docs/platform.md)
- [API contract](docs/api.md) and [JSON examples](docs/api-examples.json)
- [Testing and review workflow](docs/testing.md)
- [Verification results](docs/verification.md) and [Sprint 2 platform verification](docs/sprint-2-platform-verification.md)
- [Deployment and recovery](docs/operations.md)
- [Shared UI components](docs/shared-ui-components.md)
- [Final product acceptance](docs/final-acceptance.md)

## Repository workflow

Work is tracked as `BL-xx` backlog issues labeled by requirement type, module,
sprint, priority and Fibonacci points. Each feature lands through a focused
branch and pull request for repository-owner review; `main` must keep the Django
system check, migration consistency, isolation tests, gateway tests, React tests
and fresh-database smoke test green. Feature owners are listed in the module
labels on GitHub.

# Event Management System

A small React, Node.js and Django foundation for managing events and registrations.
The submitted SRS, architecture and test-plan documents remain at the repository root.

## Run locally

Requirements: **Python 3.11+**, **Node.js 22.12+**, and npm. SQLite is included with Python.

```text
python scripts/bootstrap.py
npm run dev
```

Open **http://127.0.0.1:5173**. API requests pass from React's development server
through Node.js and Django to SQLite.

Setup creates an ignored `.env` with random local secrets, installs pinned
dependencies, applies migrations and creates synthetic sample records. Existing
secrets and records are preserved when setup is repeated. To reuse already
installed dependencies, run `python scripts/bootstrap.py --skip-install`.

Two synthetic accounts are created: `demo-organizer-a` and `demo-organizer-b`.
Their local password is the value of `EMS_DEMO_PASSWORD` in your ignored `.env`.
Passwords are hashed in the database and are never printed by setup. Demo seeding
is disabled when `EMS_DEBUG` is not `1`.

Press **Ctrl+C** to stop the three development services. Default addresses:

| Component | Address | Responsibility |
| --- | --- | --- |
| React/Vite | 127.0.0.1:5173 | Browser interface and same-origin development proxy |
| Node.js | 127.0.0.1:3000 | Thin API gateway; forwards bodies, session cookies and CSRF tokens |
| Django | 127.0.0.1:8000 | REST modules, verified authentication, validation and data access |
| SQLite | data/events.sqlite3 | Local relational storage |

The organizer workspace implements sign-in, sign-out, event creation, owner-only
editing, confirmation-based deletion and the organizer's own event list against
the real Django session and SQLite database. Public browsing and attendee
registration are separate modules with their own issue acceptance work. There is
no pretend event API or production identity-header bypass.

## Check the platform

```text
npm test
npm run check
npm run build
npm run smoke
```

The backend suites use a disposable test database. They include a separate-process
file-database test for committed records surviving exit and pending writes rolling
back after abrupt process termination. The React suite covers validation, login,
logout and event-form states. The smoke check migrates a fresh temporary database,
seeds synthetic data, starts all three services, checks their real connection, and
stops its own processes.

Run only the organizer module with `npm run test:organizer`, or only the React
tests with `npm run test:frontend`. See the
[testing and review workflow](docs/testing.md) for commands, CI checks and the
[result-log template](docs/test-results-template.md).

To check migration consistency:

```text
node scripts/python.mjs backend/manage.py makemigrations --check --dry-run
```

## Project structure

- `backend/events/`: canonical models, migrations, repository interfaces,
  committed-write helpers, authentication adapter, fixtures command and tests.
- `backend/modules/organizer/`: organizer authentication and event mutations.
- `backend/modules/browsing/`: public event queries and attendee browse screens' APIs.
- `backend/modules/registration/`: registration and protected registrant APIs.
- `gateway/`: small Node HTTP gateway and forwarding tests.
- `frontend/`: React workspace and feature screens.
- `docs/`: API contract, data rules and verification evidence.

Feature URL modules register their own paths under `/api/`. The event collection
and event detail paths use explicit method dispatch so browsing and organizer
handlers can share a route without shadowing each other. Keep canonical
migrations in `backend/events/migrations/`; use repositories and test fixtures at
module boundaries to avoid competing production models.

## Configuration and contracts

Copyable settings are in [.env.example](.env.example). Never commit `.env`,
database files, virtual environments or dependency folders. Existing environment
variables take precedence over the local file. Choose a different database with
`EMS_DB_PATH` (relative paths resolve from the repository root).

See [architecture and data decisions](docs/platform.md),
[API contract](docs/api.md), [JSON examples](docs/api-examples.json), and
[verification results](docs/verification.md).

Feature contributors open their own PRs for repository-owner review. Whole-app
security, performance, backup/deployment and demo acceptance remain part of the
sprint milestone checks.

## Deployment and backups

Docker Compose runs the production React build, HTTPS proxy, Node gateway,
Django/Gunicorn, persistent SQLite and a backup worker. Backups run every 23 hours,
retain seven verified snapshots and restore only into a separate new database.

See [deployment, backups and recovery](docs/operations.md),
[Sprint 2 platform evidence](docs/sprint-2-platform-verification.md) and the
[final acceptance checklist](docs/final-acceptance.md).

```text
python -m unittest discover -s scripts -p test_db_backup.py -v
node scripts/python.mjs scripts/backup_smoke.py
python scripts/deploy_smoke.py
```

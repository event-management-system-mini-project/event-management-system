# Sprint 2 platform verification

Executed **28 October 2026**, based on main revision `1adadcc` plus this PR.
All records and databases used for these checks are synthetic and disposable.

Environment: Windows, Python 3.11.9, Node 24.20.0, Docker Desktop 4.92.0,
Engine 29.8.0 and Compose 5.5.1. Linux containers use Python 3.12, Node 22,
Django 5.2.18, Gunicorn 23.0.0 and Caddy 2. Deployment image digests and
Python dependencies are pinned.

| Check | Actual result |
| --- | --- |
| Backup unit tests | 8 passed |
| Platform Django suite | 25 passed |
| Organizer Django suite | 39 passed |
| Registration Django suite | 4 passed |
| Browsing Django suite | 6 passed |
| Gateway suite | 4 passed, including fixed HTTPS proxy-header handling |
| React suite | 36 passed with normal timeouts |
| Production React build | Passed |
| Django system/migration checks | Passed; no missing migrations |
| Existing development smoke | Passed |
| Canonical scheduled-backup smoke | Passed without feature servers |
| Docker configuration/image builds | Passed |
| Docker HTTPS/infrastructure smoke | Passed |

Total regression tests: **122 passed**. Existing CI remains unchanged.
`deploy/platform-ci.example.yml` supplies ready-to-enable Linux/Windows backup
checks and Linux deployment smoke. The current GitHub sign-in cannot push
workflow changes; a maintainer with workflow access can copy it to
`.github/workflows/platform.yml`. These results record local execution; remote
CI must also be checked on the PR.

## Backup evidence: NFR_03 / NFR_04

`scripts/backup_smoke.py` migrates a new canonical SQLite database and uses the
direct synthetic seed command: 2 organizers, 2 events and 1 registration. The
real scheduler creates two backups on an accelerated one-second test interval.
An isolated restore matches counts, SQLite integrity and foreign keys; the
source remains unchanged. No feature UI/API is running.

The focused tests cover committed WAL data, exclusion of pending writes,
checksum corruption, foreign-key corruption, retention, failed-attempt health
and recovery, stale detection, schedule selection and overwrite refusal.
A controlled clock checks the 24-hour freshness boundary; this is not a claim
of a day-long elapsed run.

Production uses a 23-hour interval and 60-second polling, seven verified restore
points, failure reporting and retries. Daily operation requires an always-on
host, persistent storage, disk-space monitoring and off-host backup copies.

## Infrastructure evidence

`scripts/deploy_smoke.py` created a uniquely named disposable Linux stack and
verified these actual operations:

1. Fresh migrations and healthy backend, gateway and backup services.
2. Certificate-verified HTTPS using the test Caddy CA, React production HTML,
   HSTS, and API routing through Node/Django to SQLite.
3. Real session login with Secure/HttpOnly cookies, CSRF-protected event creation
   and a canonical synthetic registration fixture.
4. A mutation without a CSRF token receives 403.
5. Session and committed event survive a backend restart.
6. A stopped backend returns safe JSON 502; the service can be started again.
7. Repeated scheduled snapshots on an isolated two-second interval restore
   organizer/event/registration counts and valid relationships.

The final smoke passed after pinning base images. An intermediate rebuild had
a temporary registry DNS failure and was rerun successfully. The script removed
only its own test containers/volumes. The local database and secrets were not
modified. Detailed metadata is in ignored `deploy/evidence/infrastructure.json`;
the optional CI template uploads its own execution artifact when enabled.

## Remaining acceptance

Deployment configuration, executable checks, scheduled backups, recovery
instructions and the final traceability template are supplied. Public hosting,
real DNS/certificate issuance, off-host backup operation, whole-product timing,
the final video and documentation freeze still require final execution on the
chosen host. See [final acceptance](final-acceptance.md).
Repository-owner review remains required before merge.

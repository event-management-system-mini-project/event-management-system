# Deployment and recovery

The Linux Docker Compose configuration runs a built React site behind Caddy,
the Node gateway, Gunicorn/Django, persistent SQLite storage and a backup worker.
Only Caddy publishes ports. The API services use a private Docker network.
Application processes run as unprivileged users. Keep this single-host setup to
one backend replica; SQLite is not a multi-host shared database.

## Start

Install Docker Engine/Desktop with Compose. From the repository root, copy
`deploy/.env.example` to `deploy/.env`. Set `EMS_SECRET_KEY` to a fresh random
value of at least 32 characters. Generate one with:

```text
python -c "import secrets; print(secrets.token_urlsafe(40))"
```

For local TLS testing, keep the example `localhost` settings. For hosting, set
`EMS_SITE_ADDRESS` and `EMS_PUBLIC_HOST` to the same real DNS name,
`EMS_ALLOWED_HOSTS` to that hostname, and `EMS_CSRF_TRUSTED_ORIGINS` to its HTTPS
origin. Point DNS at the server and allow inbound ports 80 and 443. Caddy obtains
and renews certificates. Its certificate state has a persistent volume.
`localhost` uses Caddy's local CA; browsers need that CA installed as trusted.
The automated smoke test trusts only the test stack's exported CA.

```text
docker compose --env-file deploy/.env -f deploy/compose.yml config --quiet
docker compose --env-file deploy/.env -f deploy/compose.yml up -d --build --wait
docker compose --env-file deploy/.env -f deploy/compose.yml ps
```

Migrations finish before backend/backup startup. Production disables debug and
demo seeding; create an organizer account interactively:

```text
docker compose --env-file deploy/.env -f deploy/compose.yml exec backend python backend/manage.py createsuperuser
```

Visit the configured HTTPS origin. `/api/health` checks the actual database.
Health checks mark backend, gateway and backups unhealthy on failure; restart
policies restart exited services, not merely unhealthy services. Check health
regularly with `compose ps` or an external host monitor and investigate alerts.
There is no automatic external notification service included.

## HTTPS and secrets

Caddy terminates TLS, serves static assets and forwards `/api/*` to Node. The
private gateway discards client identity and forwarding headers, sets the public
host from fixed configuration, and supplies the trusted HTTPS marker. Django's
proxy trust is enabled only in Compose. Do not publish gateway/backend ports or
enable this trust on a service directly reachable by clients. Secure/HttpOnly
session cookies, CSRF checks, HTTPS redirects and HSTS remain enabled.

Keep both `.env` files private and outside version control. Container image
builds exclude local secrets, databases, backups, dependency folders and Git.
Never run an unredacted `compose config` in shared logs; use `config --quiet`.
Request/access logging is disabled by default; operational errors and backup
status exclude submitted records and credentials. Avoid enabling body, cookie,
authorization or query-string logging in a host proxy or monitoring service.

## Backups

The worker makes an initial snapshot, checks freshness every 60 seconds, and
creates the next backup after 23 hours. This leaves margin below the 24-hour
requirement while the host is running. On restart it immediately catches up if
needed. Failed attempts produce a failure marker, unhealthy status and safe
operational output; the worker retries on its next check. Backups use SQLite's
online backup API, include committed WAL data, and exclude uncommitted writes.

Seven completed verified snapshots are retained. Each has a SHA-256 manifest,
UTC timestamp and organizer/event/registration counts. Backup files/directories
use private Linux permissions; Windows deployments must use a private NTFS
location with suitable user access controls. Corrupt/unpaired files are retained
for investigation rather than silently removed. Monitor their disk use.

The Compose `backups` volume is separate from `database`; neither is web-served.
This protects against application/container restarts, **not loss of the Docker
host or disk**. Copy verified snapshot/manifest pairs to protected encrypted
off-host storage using the host's backup service. A sleeping/free-tier host
cannot guarantee 24-hour backups or reliable TLS renewal; use an always-on host
with persistent volumes. Set disk-space and backup-age alerts on that host.

Local commands (use an existing initialized database):

```text
node scripts/python.mjs scripts/db_backup.py backup
node scripts/python.mjs scripts/db_backup.py status
node scripts/python.mjs scripts/db_backup.py run
node scripts/python.mjs scripts/db_backup.py verify --snapshot backups/REPLACE.sqlite3
node scripts/python.mjs scripts/db_backup.py restore --snapshot backups/REPLACE.sqlite3 --destination restores/check.sqlite3
```

`run` stays running and implements the schedule; a single `backup` invocation
does not schedule anything. Configure a host service to keep `run` alive when
using it outside Compose. `status` exits nonzero if the latest attempt failed,
the newest snapshot is corrupt, absent or older than 24 hours. Restore validates
checksum, SQLite integrity, foreign keys and counts, and only creates a new
destination. Existing files, the working database and the backup directory are
refused. Do not copy a live SQLite file with ordinary filesystem copy tools.

Compose operations:

```text
docker compose --env-file deploy/.env -f deploy/compose.yml exec backups python scripts/db_backup.py status
docker compose --env-file deploy/.env -f deploy/compose.yml exec backups python scripts/db_backup.py backup
docker compose --env-file deploy/.env -f deploy/compose.yml exec backups python -c "from pathlib import Path; print('\n'.join(p.name for p in sorted(Path('/backups').glob('events-*.sqlite3'))))"
docker compose --env-file deploy/.env -f deploy/compose.yml exec backups python scripts/db_backup.py restore --snapshot /backups/REPLACE.sqlite3 --destination /tmp/restore-check.sqlite3
```

For recovery, first restore and inspect a separate database, then stop application
writers. Preserve the damaged database and its SQLite sidecars for investigation.
Have the operator deliberately promote the verified restore into the database
volume with UID/GID 10001 ownership, then restart and run the health/login/data
checks. The restore command deliberately does not automate replacing live data.
Keep the matching application revision and migration history for each restore.

Normal shutdown retains volumes:

```text
docker compose --env-file deploy/.env -f deploy/compose.yml down
```

Do not use `down --volumes` for the working deployment: it deletes stored data.
The automated smoke script uses that option only for its own randomly named,
disposable test project.

## Reproducible infrastructure verification

```text
python -m unittest discover -s scripts -p test_db_backup.py -v
node scripts/python.mjs scripts/backup_smoke.py
python scripts/deploy_smoke.py
```

The backup smoke uses canonical migrations and direct synthetic seeding, runs two
scheduled backups and verifies an isolated restore without any feature servers.
The deployment smoke creates a unique isolated stack, checks certificate-verified TLS,
static serving, health/API routing, secure-cookie login and CSRF, committed data
and session persistence after restart, safe backend failure, repeated scheduled
backups, and isolated restore with canonical synthetic relationships. Its test
schedule is accelerated to two seconds; the deployed default remains 23 hours.
It removes only its own test containers/volumes and writes metadata evidence to
ignored `deploy/evidence/infrastructure.json`. It never touches local `.env`,
the local development database or the normal Compose deployment.

`deploy/platform-ci.example.yml` provides the Linux/Windows backup checks and
Linux deployment smoke as an optional workflow. A maintainer with workflow
access can copy it to `.github/workflows/platform.yml` to enable these checks
and artifact uploads. The existing CI remains unchanged.

See [Sprint 2 evidence](sprint-2-platform-verification.md) and the
[final acceptance checklist](final-acceptance.md). A local Docker result does not
establish public-host availability, DNS/TLS issuance or complete feature timing.

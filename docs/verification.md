# Platform verification

Executed on **20 October 2026**.

Environment: Windows, Python 3.11.9, Django 5.2.18, SQLite 3.45.1,
Node.js 24.20.0, React 19.3.1 and Vite 8.3.4. Dependency versions are locked
in `backend/requirements.txt` and `package-lock.json`.

## Results

| Check | Actual result |
| --- | --- |
| `python scripts/bootstrap.py` | Passed: pinned dependencies installed, migrations applied, synthetic data seeded; repeating setup preserved existing records and secrets |
| Backend test suite | 25 passed; no failures |
| Node gateway test suite | 3 passed; no failures |
| `npm run check` / Django system check | Passed; no issues |
| Migration consistency check | Passed; no model changes missing migrations |
| `npm run build` | Passed; React production assets generated |
| `npm run smoke` | Passed using a newly migrated temporary SQLite database; frontend development server -> Node gateway -> Django -> SQLite returned healthy; test services stopped afterward |
| Browser connection check | Passed: the running React page displayed Connected after calling the real gateway/Django/database path |

## Data and integrity evidence

- Valid name/description boundaries are accepted; blank, overlong and past-event
  data is rejected.
- Database constraints reject invalid lengths and same-event normalized-email
  duplicates even when ordinary model save validation is bypassed.
- The same email is accepted on different events. The database-generated
  normalized email stays in sync after updates.
- Foreign keys reject orphan registrations. Organizer deletion is protected while
  events exist; explicit event deletion removes linked registrations.
- Event and registration repository calls return after the outermost commit.
  Simulated event/registration commit failures return no result and leave no
  partial records; the pre-existing event survives a failed registration commit.
- A failure injected after event and registration writes rolls back both records.
  An outer transaction cannot conceal an uncommitted inner acknowledgement.
- A separate writer process commits to a new file database and exits; a separate
  reader sees the stored event and registration. A later process exits abruptly
  inside an unfinished transaction; the next reader sees only the committed
  records and no success acknowledgement from the interrupted write.
- Synthetic seeding creates two organizer identities, two future events and one
  registration; repeated seeding is idempotent and production-mode seeding is
  rejected.
- Anonymous/spoofed identity is rejected. The active authenticated Django user is
  the identity source; client-supplied owner overrides are not accepted by the
  event repository.
- Gateway checks exercise real local HTTP forwarding of method/body/query,
  session cookie, CSRF header and response cookie/status, stripping spoofed
  identity/proxy headers. An unavailable API produces a safe JSON error.

## Requirement traceability and limits

The database-layer portions of REQ1_IT_02, REQ3_IT_02 and REQ4_IT_02 have direct
model/repository evidence. NFR_03 has platform commit/rollback/restart evidence.
These results do **not** mark unimplemented UI/API system cases as passed.

Organizer login and event-management endpoints, attendee browsing/registration
screens, owner permissions and their complete-system integration are separate
feature work. They still need the submitted UT/IT/ST/security tests on the
integrated application. No claim is made here for the SRS's end-user response-time
thresholds, daily backups/restore, deployment readiness or demo videos.

SQLite process-restart checks are not a guarantee against every power, storage or
cloud-sync failure. A repository-owner PR review is still required before merge.

# Sprint 1 organizer verification

Executed on **22 October 2026** on Linux x86_64 with Python 3.12.3, Django 5.2.18,
SQLite 3.45.1, Node.js 24.14.1, npm 11.13.0, React 19.3.1, Vite 8.3.4 and
Vitest 5.0.5. Commands are listed in the [testing workflow](testing.md).

## Automated results

| Check | Actual result |
| --- | --- |
| `python backend/manage.py test modules.organizer` | 21 passed; no failures |
| `python backend/manage.py test events.tests` | 25 passed; no failures |
| `npm run test:gateway` | 3 passed; no failures |
| `npm run test:frontend` | 15 passed in 2 files; no failures |
| `npm run check` | Passed; no issues |
| `makemigrations --check --dry-run` | Passed; no model changes missing migrations |
| `npm run build` | Passed; production assets generated |
| `npm run smoke` | Passed with a fresh temporary SQLite database through React, Node gateway and Django |
| GitHub Actions CI | All three jobs passed on the Sprint 1 branch/PR: [run 39757163191](https://github.com/event-management-system-mini-project/project-documentation/actions/runs/39757163191) |

## Organizer evidence

- Login creates a real Django session, returns only the organizer id/username,
  and never returns or logs the submitted password or session key. Invalid and
  inactive credentials return the same clear 401 error.
- Session and login responses set a CSRF cookie; login and logout are rejected
  without a valid token. Logout removes the session; a protected create then
  returns 401.
- Anonymous requests and requests with a spoofed `X-Organizer-Id` cannot create or
  list events. Denial happens before the repository is called.
- Event creation accepts 100-character names and 1000-character descriptions;
  blank, 101-character, 1001-character, malformed-date and past-date inputs return
  field-level 400 errors.
- A client-supplied `organizer_id` does not change ownership. The saved event
  appears only in the signed-in organizer's list, ordered by date and time, and
  not in another organizer's list.
- A simulated database failure returns 503 `database_unavailable` with no event
  and no internal SQL detail. A simulated commit failure returns 503 and leaves
  zero committed events.
- Manual integrated check through the Vite proxy and Node gateway: session 200,
  login 200, create 201, organizer list 200, logout 200, then protected create
  401 with a valid CSRF token.
- Browser check: the React login screen and organizer dashboard rendered, the
  signed-in organizer's events appeared, and no console errors were reported.

## Limits

This run covers the isolated organizer module and the local integrated path. It
does not claim edit/delete (Sprint 2), attendee browsing/registration, production
deployment, backup/restore or the SRS's end-user response-time thresholds.
GitHub Actions runs the same commands on push and pull request; the PR records
the run result.

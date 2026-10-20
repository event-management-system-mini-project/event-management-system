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

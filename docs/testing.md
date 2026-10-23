# Organizer testing and review workflow

This page covers the Sprint 1 and Sprint 2 organizer module: authentication,
protected actions, event creation, owner edit/delete and the automated checks
around them. It also explains how another feature module adds its tests to the
same commands.

## Local setup

```text
python scripts/bootstrap.py
```

The backend commands use the ignored `.venv` created by setup. They use a
disposable test database, so local event data is not modified.

## Commands

| Command | Scope |
| --- | --- |
| `npm run test:organizer` | Real organizer handlers only: session/login/logout, CSRF, create/edit/delete validation, owner isolation, denial timing, commit failure |
| `npm run test:registration` | Registration route success, duplicate prevention, missing input and unknown events |
| `npm run test:backend` | Platform models, repositories and authentication adapter |
| `npm run test:gateway` | Node gateway forwarding and identity-header stripping |
| `npm run test:frontend` | React validation, login/logout, create/edit forms, delete confirmation and failure-state tests |
| `npm test` | All of the above |
| `npm run check` | Django system check |
| `npm run build` | Production React build |
| `npm run smoke` | Fresh temporary SQLite database plus React, gateway and Django services |

Useful narrower commands:

```text
node scripts/python.mjs backend/manage.py test modules.organizer.tests.test_auth --verbosity 2
node scripts/python.mjs backend/manage.py test modules.organizer.tests.test_events --verbosity 2
node scripts/python.mjs backend/manage.py test modules.organizer.tests.test_edit_delete --verbosity 2
node scripts/python.mjs backend/manage.py makemigrations --check --dry-run
npm run test:frontend -- src/validation.test.js
```

The organizer tests run without the platform suite:

```text
node scripts/python.mjs backend/manage.py test modules.organizer --verbosity 2
```

## Test data and identity

- Backend fixtures live in `backend/modules/organizer/tests/support.py`. They
  create synthetic organizers with hashed passwords and log in through Django's
  real session backend.
- There is no test identity header, query parameter or production bypass. The
  only identity source is `events.auth.authenticated_organizer(request)`.
- Test-only repository doubles are patched inside test functions. Production
  handlers always import the canonical `DjangoEventStore`.
- Edit/delete tests measure the complete handler denial path with a monotonic
  clock and assert it stays under one second. The test output prints the observed
  edit/delete denial times for the local run.
- Tests use synthetic names, passwords and event details only. Logs are checked
  for submitted passwords and session identifiers.
- The gateway test proves `X-Organizer-Id` and forwarding headers are stripped.

## Adding a module test

1. Create `backend/modules/<name>/tests/__init__.py`.
2. Use `django.test.TestCase` against the real handler and a disposable database.
3. Put reusable synthetic fixtures in the module's `tests/` package, never in a
   production module.
4. Run the suite in isolation, then add it to `package.json` and the backend CI
   job. Do not add a CI-only identity shortcut to application code.
5. Record the command, environment, expected result and actual result in the
   [result log](test-results-template.md).

## CI checks

`.github/workflows/ci.yml` runs on every push and pull request:

- Django system check and migration consistency.
- Platform and organizer test suites as separate jobs.
- Gateway and React tests plus the production build.
- A fresh-database smoke test through React, Node and Django.

CI uses placeholder credentials supplied as environment values. It never uses a
real password, session token or attendee record, and it does not print those
values.

## Contributor and repository-owner workflow

1. Create a feature branch from `main` and open a pull request that links the
   issue (`Closes #3`, for example).
2. Confirm all CI jobs pass. Attach the result log for anything that cannot be
   reproduced in CI.
3. Ask a repository owner to review the diff, test commands and test evidence.
4. The repository owner merges only after the checks and review are complete.
5. Record remaining whole-system checks in the sprint milestone checklist.

Automated module tests are **isolated checks**. They prove handler behavior,
validation, authorization and commit handling. They do not replace an integrated
acceptance run through the real React UI, gateway, Django service and canonical
database, or the security/performance checks tracked at sprint level.

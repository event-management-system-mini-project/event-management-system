# Unit and module test report

Execution recorded: 2026-11-19T05:39:24.305219+00:00. Tested baseline: main 902288c with report instrumentation only. Planned course testing window: 2-6 November 2026. These are actual November 19 execution records, not historical execution claims.

Outcome: all automated regression suites passed. These suites include unit, component and database integration tests; the total is not a count of pure unit tests.

| Suite | Passed | Evidence |
| --- | ---: | --- |
| Django combined discovery | 79 | evidence/backend-tests.txt |
| React components and API helper | 42 | evidence/frontend-tests.txt |
| Node gateway | 4 | evidence/gateway-tests.txt |
| Backup and isolated restore | 8 | evidence/backup-tests.txt |
| Total | 133 | All suites above |

Run backend with `.venv/Scripts/python.exe -m coverage run backend/manage.py test events.tests modules.organizer modules.registration modules.registrants modules.browsing --verbosity 2`. Run backup tests with `coverage run --append -m unittest discover -s scripts -p test_db_backup.py -v`; run frontend with `npm run test:frontend -- --coverage`; gateway with `npm run test:gateway`.

Linux uses `.venv/bin/python` instead. No real attendee data or production database was used. Disposable test databases are destroyed by the runners. Dates and dependency/runtime environment are recorded in the evidence manifest.

The existing registrant-owner test supplies an identity header rather than proving a session. Its passing result does not validate secure ownership; the independent system probe exposes the defect. Existing CI also omits explicit browsing discovery and the optional platform workflow. Full system acceptance is assessed separately.


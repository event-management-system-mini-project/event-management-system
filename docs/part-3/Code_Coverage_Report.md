# Code coverage report

Execution recorded: 2026-11-19T05:39:24.305219+00:00. Tested baseline: main 902288c with report instrumentation only. Planned course testing window: 2-6 November 2026. These are actual November 19 execution records, not historical execution claims.

Measured executable code coverage:

| Scope | Metric | Covered / total | Percent |
| --- | --- | --- | ---: |
| Python application and backup worker | Statements | 603 / 740 | 81.49% |
| React src | Lines | 321 / 351 | 91.45% |
| React src | Statements | 338 / 381 | 88.71% |
| Node gateway server.mjs | Lines | See Node report | 91.04% |

Python: coverage.py 7.17.3 with branch tracing; JSON at `coverage/backend.json`, browsable HTML at `coverage/backend/index.html`. React: Vitest/V8 5.0.5; `coverage/frontend/index.html` and `coverage/frontend/coverage-summary.json`. Node built-in coverage: `evidence/gateway-coverage.txt`; test files excluded.

Python scope includes backend application modules and scripts/db_backup.py, excluding test code, migrations, __init__ files, management launcher and operational smoke/benchmark/bootstrap scripts. Frontend scope includes all src JS/JSX including unexecuted entry/example components, excluding tests/setup. Third-party dependencies and generated bundles are excluded. Separate denominators are reported rather than combining different instrumentation semantics into one misleading percentage.

Unexecuted/partially covered code includes legacy unattached handlers, deployment-only WSGI paths, failure paths, frontend entry/example components and branch-specific UI states. Raw reports identify exact lines. Coverage is execution evidence, not proof of requirement correctness or privacy. No coverage target was specified by the course PDF; unmet security/system requirements still block acceptance.


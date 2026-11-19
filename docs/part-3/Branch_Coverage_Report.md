# Branch coverage report

Execution recorded: 2026-11-19T05:39:24.305219+00:00. Tested baseline: main 902288c with report instrumentation only. Planned course testing window: 2-6 November 2026. These are actual November 19 execution records, not historical execution claims.

| Scope | Covered / total branch outcomes | Coverage |
| --- | --- | ---: |
| Python application and backup worker | 89 / 136 | 65.44% |
| React src | 276 / 354 | 77.96% |
| Node gateway server.mjs | See built-in report | 79.17% |

Python has 47 missing branch outcomes and 23 partial branches. Python arcs are recorded in coverage/backend.json (executed_branches and missing_branches) and the HTML annotation. Frontend V8 branch locations and counters are in coverage/frontend/coverage-final.json and its HTML report. Node percentages come directly from the filtered built-in coverage output.

Scope/exclusions match Code_Coverage_Report.md. Python arcs, V8 branch outcomes and Node built-in branch accounting use different definitions; their values must not be averaged. The Python combined coverage percentage includes both statements and arcs and is not the statement-only percentage reported separately.

Priority follow-up: session-owner/forged-ID/nonowner/anonymous registrant branches, malformed JSON types, registration database exceptions, route agreement and event-details UI. Tests must assert the intended secure outcomes; exercising an insecure success branch is insufficient. The included failing system probes provide a concrete starting point.


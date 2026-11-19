# System validation report

Execution recorded: 2026-11-19T05:39:24.305219+00:00. Tested baseline: main 902288c with report instrumentation only. Planned course testing window: 2-6 November 2026. These are actual November 19 execution records, not historical execution claims.

Outcome: **NOT ACCEPTED for final release**. 12 of 19 targeted checks passed; 7 failed. These are HTTP-client and source-wiring checks, not an executed full-browser test suite.

| Check | Expected | Actual | Result |
| --- | --- | --- | --- |
| health | 200 | 200 | PASS |
| public_list | 200 | 200 | PASS |
| public_detail | 200 | 200 | PASS |
| anonymous_create_denied | 401 | 401 | PASS |
| valid_registration | 201 | 201 | PASS |
| duplicate_rejected | 400 | 400 | PASS |
| duplicate_single_row | 1 | 1 | PASS |
| missing_name | 400 | 400 | PASS |
| invalid_email | 400 | 400 | PASS |
| long_name | 400 | 400 | PASS |
| null_name_validation | 400 | 500 | FAIL |
| database_failure | 503 | 500 | FAIL |
| anonymous_registrants_denied | 403 | 403 | PASS |
| forged_identity_denied | 403 | 200 | FAIL |
| session_owner_registrants | 200 | 403 | FAIL |
| frontend_registrants_route | 200 | 404 | FAIL |
| canonical_registration_route | 201 | 404 | FAIL |
| registration_form_connected | True | True | PASS |
| details_screen_connected | True | False | FAIL |

Repeat with `node scripts/python.mjs scripts/part3_validate.py`. Exit 1 is intentional while requirements fail. Output is `evidence/system-validation.json`; fixtures are created in a temporary database. Product code is not patched by the probes.

Critical defect: registrant listing trusts supplied organizer identity and exposes attendee names/emails anonymously. Fix verified-session ownership first. Other defects: no event-details screen, slash/route mismatch, null-input crash and inconsistent registration failure response. Registration from the event list is now connected through PR 39; component coverage and prior real browser verification are recorded separately.

Production build, migration consistency, development smoke and canonical backup smoke passed in this run. Current API benchmark uses 100 events and 15 samples; see `evidence/api-benchmark.json`. It measures requests through the gateway, not browser rendering or end-user timing. No new public-host, cross-browser, 24-hour soak or production TLS run is claimed. The earlier Docker smoke remains historical evidence in the Sprint 2 report.

The case ledger in Updated_Test_Cases.csv classifies every original case and the sprint amendments. MODULE PASS means relevant automated assertions passed; PARTIAL and NOT RUN do not count as final system acceptance. Full browser creation/edit/deletion, inaccessible event-details navigation, final privacy checks and timing need completion or retest. Remaining failures require correction and retesting; no defect was waived. Optional Sprint 3 development is excluded.


# System validation report

Execution recorded: 2026-11-19T06:40:15.720884+00:00. Browser follow-up: 19 November 2026. Tested baseline: main 42f9afd with report instrumentation only. Planned course testing window: 2-6 November 2026. These are actual November 19 execution records, not historical execution claims.

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

Production build, migration consistency, development smoke and canonical backup smoke passed in this run. Current API benchmark uses 100 events and 15 samples; see `evidence/api-benchmark.json`. It measures requests through the gateway, not browser rendering or end-user timing. A fresh Docker HTTPS/restart/backup smoke passed; evidence/deployment.json records the actual run. No public-host, cross-browser or continuous 24-hour soak is claimed.

All 55 case outcomes are now filled: {'PASS': 47, 'FAIL': 7, 'BLOCKED': 1}. The original Test Plan and companion ledger agree. Browser creation/edit/deletion, invalid required fields, cancellation, guest registration, duplicate rejection, logout and empty/past-event states passed. Details navigation and privacy defects remain failed. Continuous 24-hour backup evidence is BLOCKED. Optional Sprint 3 development is excluded.


## Browser follow-up results

| Case | Result | Actual evidence |
| --- | --- | --- |
| NFR_01 | PASS | Local page reload to observed event list; automation-inclusive elapsed time. 230 ms. |
| REQ4_ST_01 | PASS | Guest inline registration confirms success and refreshes count to one. |
| NFR_02 | PASS | Local submit to observed confirmation; automation-inclusive upper bound. 320 ms. |
| REQ4_ST_02 | PASS | Repeated email rejected with count unchanged at one. |
| REQ1_ST_02 | PASS | Empty create form rejected with field errors. |
| REQ1_ST_01 | PASS | Login and real browser creation succeeded; dated 2099-02-02 12:00, visible in owner and public lists. |
| REQ2_ST_01 | PASS | Changed location through edit form; Updated Hall appeared in both public and owner lists. |
| REQ2_UT_03 | PASS | Incomplete edited name rejected with a required-field error. |
| delete_cancel | PASS | Cancellation preserved the synthetic event. |
| REQ2_ST_02 | PASS | Confirmed owner delete removed event; nonowner denial verified separately by real backend tests. |
| REQ3_ST_02 | PASS | After the only remaining synthetic event was made past, browser displayed No upcoming events; no past event card was shown. |
| REQ3_UT_03 | PASS | Empty upcoming list displays a clear message without an error. |
| REQ3_ST_01 | FAIL | Inspected public cards: no event-details link or screen exists. |
| REQ3_IT_01 | PASS | Real browser displayed created/edited public event data and refreshed after deletion. |
| REQ4_IT_01 | PASS | Browser form posted name/email to real gateway/backend and showed confirmed count. |
| REQ1_IT_01 | PASS | Real create form posted valid event data; public and owner lists updated. |

Browser flows used a disposable SQLite database, synthetic accounts, isolated ports and a correctly trusted test origin. Source-code defects were not fixed.

# Final product acceptance

Record actual evidence for the integrated application before the development
freeze. Infrastructure checks alone do not establish feature acceptance.

| Requirement | Evidence to record | Status |
| --- | --- | --- |
| REQ-1: create event | Valid and invalid form/API flow, committed data | Pending final run |
| REQ-2: edit/delete | Owner success, cancellation, nonowner denial, cleanup | Pending final run |
| REQ-3: browse/details | Future ordering, details, aggregate counts | Pending final run |
| REQ-4: register | Success, validation, duplicate rejection and refreshed count | Pending final run |
| SEC-1/2 | Real session identity, anonymous/nonowner denial, no writes on denial | Pending final run |
| SEC-3/privacy | Owner-only attendee data, safe public payloads/logs, TLS | Pending final run |
| NFR performance | List <2s, detail within 2s, registration within 3s, denial within 1s; environment and repeated samples | Pending final run |
| NFR integrity/backup | Restart retention, failed writes, scheduled snapshot and isolated restore | See platform evidence; repeat on target host |
| Deployment | Real DNS, valid certificate, protected secrets and persistent storage | Pending target-host run |
| Documentation | SRS/SAD/Test Plan deviations, final test results and run/recovery instructions | Pending final review |
| Delivery workflow | Contributor PRs and recorded repository-owner reviews | Pending review |
| Demonstration | Two-minute working-product video committed to repository | Pending recording |
| Freeze | Final approved revision and development freeze date | Pending |

For every final run record: revision, date, environment/browser, synthetic dataset,
command or steps, expected result, actual result, pass/fail and evidence link.
Use [the result template](test-results-template.md). Keep personal information and
credentials out of screenshots, recordings and logs.

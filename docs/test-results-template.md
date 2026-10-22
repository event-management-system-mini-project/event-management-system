# Test result log

Copy this template into the PR or sprint record. Use synthetic data only. Do not
paste passwords, session tokens, `.env` contents or real attendee information.

## Build and environment

| Item | Value |
| --- | --- |
| Date and time | |
| Branch / commit | |
| Issue(s) | |
| Operating system | |
| Python / Django | |
| Node.js / npm | |
| Database | |
| Browser (if applicable) | |
| Command(s) | |

## Results

| ID | Check | Expected | Actual | Duration | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| SEC_01 | Anonymous and spoofed identity denied | 401 JSON, no repository write | | | | |
| REQ1_ST_01 | Organizer login and protected action | Session login; protected action allowed | | | | |
| REQ1_UT_01–06 | Event validation boundaries | 100/1000 accepted; 101/1001 and blank rejected | | | | |
| REQ1_IT_01 | Event write committed before success | 201 only after durable commit | | | | |
| REQ1_IT_02 | Owner isolation | Organizer sees and writes only own events | | | | |
| REQ1_ST_02 | Organizer event list | Saved event appears in own list | | | | |
| — | Logout removes protected access | Protected action returns 401 | | | | |
| — | Database/commit failure | Clear failure, no confirmed event | | | | |
| — | CI checks on commit/PR | All jobs pass | | | | |

## Defects and retests

| Defect | Severity | Opened | Fix / commit | Retest result |
| --- | --- | --- | --- | --- |
| | | | | |

## Limits

Record what this run does **not** prove, for example whole-app performance,
deployment, backups/restore, or another team's module. Isolated module checks do
not replace the integrated acceptance run.

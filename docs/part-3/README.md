# Part 3 testing deliverables

Execution recorded: 2026-11-19T05:39:24.305219+00:00. Tested baseline: main 902288c with report instrumentation only. Planned course testing window: 2-6 November 2026. These are actual November 19 execution records, not historical execution claims.

This folder contains the updated test-case document/CSV and the four requested reports. Product fixes are not included in this reporting change.

- [Updated test case document](Updated_Test_Cases.docx)
- [Full executable-procedure ledger](Updated_Test_Cases.csv)
- [Unit test report](Unit_Test_Report.md)
- [System validation report](System_Validation_Report.md)
- [Code coverage report](Code_Coverage_Report.md)
- [Branch coverage report](Branch_Coverage_Report.md)

Test-case status totals (55 cases): {'MODULE PASS': 32, 'NOT RUN': 11, 'FAIL': 7, 'PARTIAL': 5}. MODULE PASS describes module evidence, not a full browser execution. See the CSV for actual results and original expected outcomes. The original root Test Plan is retained as the baseline; this revision is its Part 3 execution/amendment companion.

Automated regression: 133 passed. System validation fails release acceptance; open defects and unexecuted checks are explicitly recorded. Known defects require fixes and retesting before final acceptance. Optional Sprint 3 development is excluded. Git commit author date is separately requested as 5 November; report execution dates remain accurate.

Evidence: text logs, machine-readable system checks, timing samples, backend and frontend HTML/JSON coverage. Report rendering images stay outside the repository. No secrets, working database or local .env files are included.


## Reproduce the checks

After the normal project bootstrap, install reporting dependencies:

```text
node scripts/python.mjs -m pip install -r backend/requirements-test.txt
npm ci
node scripts/python.mjs -m coverage erase
node scripts/python.mjs -m coverage run backend/manage.py test events.tests modules.organizer modules.registration modules.registrants modules.browsing --verbosity 2
node scripts/python.mjs -m coverage run --append -m unittest discover -s scripts -p test_db_backup.py -v
node scripts/python.mjs -m coverage json -o docs/part-3/coverage/backend.json
node scripts/python.mjs -m coverage html -d docs/part-3/coverage/backend
npm run test:frontend -- --coverage
node --experimental-test-coverage --test-coverage-exclude=**/*.test.mjs --test gateway/server.test.mjs
node scripts/python.mjs scripts/part3_validate.py
```

The final command returns exit 1 while its expected requirement checks fail.
Do not reinterpret that exit as a passing result. Each new execution must update
report dates, case statuses and the evidence manifest using the new actual results.

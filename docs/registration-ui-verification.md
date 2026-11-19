# Attendee registration flow

Select **Register for [event name]** in Upcoming events, enter a name and email,
and submit. No attendee account is required. Confirmation appears after the API
accepts the registration and the event list refreshes its aggregate count.

The form uses the shared API helper, including the current CSRF token for an
existing organizer session. Duplicate/validation errors preserve the entered
details. Submission is disabled while a request is pending.

Verified on 19 November 2026:

- All 42 frontend tests passed, including guest/session registration, count
  refresh, retained confirmation, duplicate handling, pending submission and CSRF.
- Production React build passed.
- Real browser guest registration through Vite, Node and Django succeeded and
  increased the displayed count from 2 to 3 in the disposable fixture database.
- A real authenticated Django request with CSRF succeeded; repeating the email
  was rejected and left exactly one registration.

This change connects the existing registration endpoint. The separate owner-only
registrant authorization and event-details screen findings from the system
review remain outside this change.

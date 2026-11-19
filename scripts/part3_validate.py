"""Run requirement-oriented checks on a fresh disposable database; report failures honestly."""
import json
import logging
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix="ems-part3-") as temporary:
        os.environ.update(EMS_DB_PATH=str(Path(temporary) / "test.sqlite3"),
                          EMS_DEBUG="1", EMS_SECRET_KEY=secrets.token_urlsafe(40),
                          EMS_DEMO_PASSWORD=secrets.token_urlsafe(24))
        sys.path.insert(0, str(ROOT / "backend"))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        import django
        django.setup()
        from django.core.management import call_command
        from django.test import Client, override_settings
        from django.db import OperationalError
        from events.models import Event, Registration
        from unittest.mock import patch
        logging.disable(logging.CRITICAL)
        call_command("migrate", verbosity=0)
        call_command("seed_demo", verbosity=0)
        event = Event.objects.order_by("id").first()
        client = Client(raise_request_exception=False)

        def check(case, expected, actual, note=""):
            results.append(dict(case=case, expected=expected, actual=actual,
                                result="PASS" if actual == expected else "FAIL", note=note))

        def post(payload):
            return client.post(f"/api/events/{event.id}/register",
                data=json.dumps(payload), content_type="application/json")

        check("health", 200, client.get("/api/health").status_code)
        check("public_list", 200, client.get("/api/events").status_code)
        check("public_detail", 200, client.get(f"/api/events/{event.id}").status_code)
        check("anonymous_create_denied", 401, client.post("/api/events", data="{}", content_type="application/json").status_code)
        check("valid_registration", 201, post({"name": "Synthetic", "email": "part3@example.com"}).status_code)
        check("duplicate_rejected", 400, post({"name": "Synthetic", "email": "part3@example.com"}).status_code,
              "Current route returns 400; documented canonical contract specifies 409.")
        check("duplicate_single_row", 1, Registration.objects.filter(event=event, email="part3@example.com").count())
        check("missing_name", 400, post({"email": "missing@example.com"}).status_code)
        check("invalid_email", 400, post({"name": "Synthetic", "email": "invalid"}).status_code)
        check("long_name", 400, post({"name": "A" * 101, "email": "long@example.com"}).status_code)
        with override_settings(DEBUG=False):
            check("null_name_validation", 400, post({"name": None, "email": "null@example.com"}).status_code)
            with patch("modules.registration.views.Registration.objects.create", side_effect=OperationalError("synthetic")):
                check("database_failure", 503, post({"name": "Synthetic", "email": "failure@example.com"}).status_code)
        check("anonymous_registrants_denied", 403, client.get(f"/api/events/{event.id}/registrations/").status_code)
        check("forged_identity_denied", 403, client.get(f"/api/events/{event.id}/registrations/",
              {"organizer_id": str(event.organizer_id)}).status_code,
              "A supplied organizer UUID must not authenticate the request.")
        client.force_login(event.organizer)
        check("session_owner_registrants", 200, client.get(f"/api/events/{event.id}/registrations/").status_code)
        check("frontend_registrants_route", 200, client.get(f"/api/events/{event.id}/registrations").status_code)
        check("canonical_registration_route", 201, client.post(f"/api/events/{event.id}/registrations",
              data=json.dumps({"name": "Synthetic", "email": "canonical@example.com"}), content_type="application/json").status_code)
        files = [p for p in (ROOT / "frontend/src").rglob("*.jsx") if not p.name.endswith("test.jsx") and p.name != "RegistrationForm.jsx"]
        check("registration_form_connected", True, any("import RegistrationForm" in p.read_text(encoding="utf-8") for p in files))
        check("details_screen_connected", True, any("getEventDetails" in p.read_text(encoding="utf-8") for p in files),
              "No details-screen handler is connected; public detail API alone is insufficient.")
        from django.db import connections
        connections.close_all()
    report = {"executed_at": datetime.now(timezone.utc).isoformat(), "checks": results}
    output = ROOT / "docs/part-3/evidence/system-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": sum(x["result"] == "PASS" for x in results),
                      "failed": sum(x["result"] == "FAIL" for x in results)}))
    return int(any(x["result"] == "FAIL" for x in results))


if __name__ == "__main__":
    sys.exit(main())

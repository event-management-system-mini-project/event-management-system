"""Exercise deployment using a uniquely named disposable Docker Compose project.

Requires Docker Compose and built images or network access to build them. Creates
only synthetic data; removes only this run's containers and volumes on exit.
"""
import argparse
from datetime import datetime, timezone
import http.cookiejar
import json
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "deploy/evidence/infrastructure.json")
    args = parser.parse_args()
    project = "ems-check-" + uuid.uuid4().hex[:10]
    http_port, https_port = free_port(), free_port()
    while https_port == http_port:
        https_port = free_port()
    origin = f"https://localhost:{https_port}"
    results = {"executed_at": datetime.now(timezone.utc).isoformat(), "checks": []}
    password = secrets.token_urlsafe(24)
    with tempfile.TemporaryDirectory(prefix="ems-deployment-") as temporary:
        temp = Path(temporary)
        env = temp / ".env"
        env.write_text(
            f"EMS_SECRET_KEY={secrets.token_urlsafe(40)}\nEMS_SITE_ADDRESS=localhost\n"
            f"EMS_PUBLIC_HOST=localhost:{https_port}\nEMS_ALLOWED_HOSTS=localhost\n"
            f"EMS_CSRF_TRUSTED_ORIGINS={origin}\n"
            f"EMS_HTTP_PORT={http_port}\nEMS_HTTPS_PORT={https_port}\n", encoding="utf-8")
        # Exercise the real scheduling loop with a short interval in this isolated run.
        override = temp / "schedule.yml"
        override.write_text('services:\n  backups:\n    command: ["python", "scripts/db_backup.py", "run", "--interval", "2"]\n')
        compose = ["docker", "compose", "--env-file", str(env), "-f",
                   str(ROOT / "deploy/compose.yml"), "-f", str(override), "-p", project]

        def run(*command, input=None, timeout=120):
            result = subprocess.run([*compose, *command], cwd=ROOT, input=input,
                                    text=True, capture_output=True, timeout=timeout)
            if result.returncode:
                # Do not print command input or configuration containing secrets.
                raise RuntimeError("Compose operation failed: " + " ".join(command[:2])
                                   + "\n" + result.stderr[-1800:])
            return result.stdout

        def passed(message):
            results["checks"].append(message)
            print("PASS:", message, flush=True)

        try:
            run("config", "--quiet")
            run("build", timeout=600)
            run("up", "-d", "--wait", "--wait-timeout", "120", timeout=180)
            passed("Fresh migrations and healthy backend, gateway and backup services")
            # Use Caddy's real local CA, not an insecure TLS bypass.
            run("cp", "web:/data/caddy/pki/authorities/local/root.crt", str(temp / "root.crt"))
            context = ssl.create_default_context(cafile=str(temp / "root.crt"))
            cookies = http.cookiejar.CookieJar()
            client = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=context),
                urllib.request.HTTPCookieProcessor(cookies))

            def request(path, data=None, method=None):
                headers = {"Origin": origin}
                if data is not None:
                    headers["Content-Type"] = "application/json"
                    headers["X-CSRFToken"] = next(
                        (cookie.value for cookie in cookies if cookie.name == "csrftoken"), "")
                req = urllib.request.Request(origin + path,
                    data=None if data is None else json.dumps(data).encode(),
                    headers=headers, method=method)
                return client.open(req, timeout=10)

            with request("/") as response:
                assert '<div id="root"></div>' in response.read().decode()
                assert response.headers["Strict-Transport-Security"]
            with request("/api/health") as response:
                assert json.load(response)["database"] == "ok"
            passed("Certificate-verified HTTPS serves the React build and routes API to SQLite")
            fixture = '''import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from events.models import Organizer
Organizer.objects.create_user(username='infrastructure-check', password=PASSWORD)
'''.replace("PASSWORD", repr(password))
            run("exec", "-T", "-w", "/app/backend", "backend", "python", "-", input=fixture)
            with request("/api/auth/session") as response:
                assert json.load(response)["organizer"] is None
            with request("/api/auth/login", {"username": "infrastructure-check", "password": password}) as response:
                assert json.load(response)["organizer"]["username"] == "infrastructure-check"
            session = next(cookie for cookie in cookies if cookie.name == "sessionid")
            assert session.secure and session.has_nonstandard_attr("HttpOnly")
            event_data = {"name": "Infrastructure synthetic event", "description": "Disposable test",
                          "date": "2099-01-01", "time": "10:00", "location": "Synthetic Hall"}
            with request("/api/events", event_data) as response:
                assert response.status == 201
                event_id = json.load(response)["event"]["id"]
            # A registration created at the data boundary keeps this check independent
            # of registration feature routing while verifying real FK relationships.
            seed_registration = '''import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from events.models import Registration
Registration.objects.create(event_id=EVENT_ID, name='Synthetic', email='check@example.com')
'''.replace("EVENT_ID", repr(event_id))
            run("exec", "-T", "-w", "/app/backend", "backend", "python", "-", input=seed_registration)
            passed("Secure-cookie login, CSRF-protected event write and canonical registration fixture")
            try:
                client.open(urllib.request.Request(origin + "/api/events", data=b'{}',
                    headers={"Origin": origin, "Content-Type": "application/json"}), timeout=10)
                raise AssertionError("CSRF-free write was accepted")
            except urllib.error.HTTPError as error:
                assert error.code == 403
            passed("CSRF-free mutation denied")
            run("restart", "backend")
            deadline = time.monotonic() + 30
            while True:
                try:
                    with request("/api/organizer/events") as response:
                        assert event_id in [event["id"] for event in json.load(response)["events"]]
                    break
                except (urllib.error.URLError, OSError):
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.5)
            passed("Session and committed event survive backend restart on persistent storage")
            run("stop", "backend")
            try:
                request("/api/health")
                raise AssertionError("Stopped API returned healthy")
            except urllib.error.HTTPError as error:
                assert error.code == 502
                assert json.load(error)["error"]["code"] == "upstream_unavailable"
            run("start", "backend")
            passed("Stopped backend returns a safe gateway 502")
            # Wait for at least two real scheduled snapshots containing the test rows.
            check_backups = '''import sys
sys.path.insert(0, '/app/scripts')
from pathlib import Path
from db_backup import verify, restore, status
snapshots=sorted(Path('/backups').glob('events-*.sqlite3'))
assert len(snapshots)>=2
assert verify(snapshots[-1])['counts']=={'organizers':1,'events':1,'registrations':1}
restore(snapshots[-1], Path('/tmp/restore-check.sqlite3'), Path('/data/events.sqlite3'))
assert status('/backups')['status']=='ok'
'''
            deadline = time.monotonic() + 30
            while True:
                try:
                    run("exec", "-T", "backups", "python", "-", input=check_backups)
                    break
                except RuntimeError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(1)
            passed("Scheduled backups repeat and restore organizer/event/registration counts and relationships")
            results["status"] = "passed"
        finally:
            results.setdefault("status", "failed")
            # This exact random project was created above; never target the normal deployment.
            run("down", "--volumes", "--remove-orphans", timeout=60)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Evidence:", args.output)


if __name__ == "__main__":
    main()

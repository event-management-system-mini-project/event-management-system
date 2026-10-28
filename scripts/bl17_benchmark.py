
"""BL-17 repeatable API benchmark using a disposable SQLite database.

Measures API response times through the Node gateway. It does not measure
browser rendering or action-to-visible-result time.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import date, timedelta
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
MANAGE = ROOT / "backend" / "manage.py"
GATEWAY = ROOT / "gateway" / "server.mjs"

OWNER_ID = "00000000-0000-4000-8000-000000000001"
OTHER_ID = "00000000-0000-4000-8000-000000000002"
FIRST_EVENT_ID = "00000000-0000-0000-0000-0000000003e8"
TEST_PASSWORD = "BL17-Local-Benchmark-Only-2026!"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def percentile95(values):
    ordered = sorted(values)
    index = max(0, int(0.95 * len(ordered) + 0.999999) - 1)
    return ordered[index]


def summarize(samples):
    return {
        "samples": len(samples),
        "min_ms": round(min(samples), 3),
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(percentile95(samples), 3),
        "max_ms": round(max(samples), 3),
    }


def request_json(opener, url, method="GET", body=None, headers=None):
    request_headers = {"Accept": "application/json"}
    request_headers.update(headers or {})
    data = None

    if body is not None:
        request_headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    request = Request(
        url,
        data=data,
        headers=request_headers,
        method=method,
    )

    started = time.perf_counter()
    try:
        with opener.open(request, timeout=10) as response:
            status = response.status
            raw = response.read()
    except HTTPError as error:
        status = error.code
        raw = error.read()
    elapsed_ms = (time.perf_counter() - started) * 1000

    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {}

    return status, payload, elapsed_ms


def make_opener():
    cookie_jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))
    opener.bl17_cookie_jar = cookie_jar
    return opener


def seed_database(env, event_count):
    seed_code = f"""
import uuid
from datetime import timedelta
from django.utils import timezone
from events.models import Event, Organizer

owner = Organizer.objects.create_user(
    pk=uuid.UUID("{OWNER_ID}"),
    username="bl17-benchmark-owner",
    password="{TEST_PASSWORD}",
)
other = Organizer.objects.create_user(
    pk=uuid.UUID("{OTHER_ID}"),
    username="bl17-benchmark-other",
    password="{TEST_PASSWORD}",
)

today = timezone.localdate()
events = []
for i in range({event_count}):
    events.append(Event(
        id=uuid.UUID(int=1000 + i),
        organizer=owner,
        name=f"Synthetic BL17 event {{i + 1}}",
        description="Synthetic benchmark fixture",
        date=today + timedelta(days=1 + (i % 365)),
        time="10:00:00",
        location="Synthetic Test Hall",
    ))
Event.objects.bulk_create(events)
print("BL17_SYNTHETIC_FIXTURES_READY")
"""
    subprocess.run(
        [sys.executable, str(MANAGE), "shell", "-c", seed_code],
        cwd=ROOT,
        env=env,
        check=True,
        timeout=60,
    )


def wait_until_ready(base_url, children):
    deadline = time.monotonic() + 25
    last_error = None

    while time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            raise RuntimeError("A service exited before becoming ready.")

        try:
            status, payload, _ = request_json(
                make_opener(), urljoin(base_url, "/api/health")
            )
            if status == 200 and payload.get("status") == "ok":
                return
        except (URLError, OSError, TimeoutError) as error:
            last_error = error

        time.sleep(0.2)

    raise RuntimeError(f"Services did not become ready. Last error: {last_error}")


def get_csrf(opener, base_url):
    status, _, _ = request_json(
        opener, urljoin(base_url, "/api/auth/session")
    )

    if status != 200:
        raise RuntimeError(
            f"Could not obtain a CSRF cookie: HTTP {status}"
        )

    for cookie in opener.bl17_cookie_jar:
        if cookie.name == "csrftoken":
            return cookie.value

    raise RuntimeError(
        "Django did not set the expected CSRF cookie."
    )


def login(opener, base_url, username):
    csrf = get_csrf(opener, base_url)
    status, _, _ = request_json(
        opener,
        urljoin(base_url, "/api/auth/login"),
        method="POST",
        body={"username": username, "password": TEST_PASSWORD},
        headers={"X-CSRFToken": csrf},
    )
    if status != 200:
        raise RuntimeError(f"Benchmark login failed: HTTP {status}")

    return get_csrf(opener, base_url)


def main():
    parser = argparse.ArgumentParser(
        description="Run BL-17 API timing measurements on temporary SQLite."
    )
    parser.add_argument(
        "--events",
        type=int,
        default=100,
        help="Number of synthetic events (1–5000; default 100).",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=15,
        help="Measured requests per action (1–200; default 15).",
    )
    parser.add_argument(
        "--output",
        default="reports/bl17-benchmark.json",
        help="JSON report output path.",
    )
    args = parser.parse_args()

    if not 1 <= args.events <= 5000:
        parser.error("--events must be between 1 and 5000.")
    if not 1 <= args.iterations <= 200:
        parser.error("--iterations must be between 1 and 200.")

    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required to run the gateway.")
    if not GATEWAY.exists() or not MANAGE.exists():
        raise SystemExit("Run this script from the project repository.")

    backend_port = free_port()
    gateway_port = free_port()
    while gateway_port == backend_port:
        gateway_port = free_port()

    children = []
    results = {}
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    base_url = f"http://127.0.0.1:{gateway_port}"

    with tempfile.TemporaryDirectory(prefix="ems-bl17-") as temporary:
        db_path = str(Path(temporary) / "bl17.sqlite3")
        env = {
            **os.environ,
            "EMS_DEBUG": "1",
            "EMS_DB_PATH": db_path,
            "EMS_DEMO_PASSWORD": TEST_PASSWORD,
            "DJANGO_UPSTREAM": f"http://127.0.0.1:{backend_port}",
            "GATEWAY_HOST": "127.0.0.1",
            "GATEWAY_PORT": str(gateway_port),
        }

        with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as logs:
            try:
                subprocess.run(
                    [
                        sys.executable, str(MANAGE),
                        "migrate", "--noinput",
                    ],
                    cwd=ROOT, env=env, check=True, timeout=60,
                    stdout=logs, stderr=logs,
                )

                seed_database(env, args.events)

                children.append(subprocess.Popen(
                    [
                        sys.executable, str(MANAGE),
                        "runserver", f"127.0.0.1:{backend_port}", "--noreload",
                    ],
                    cwd=ROOT, env=env, stdout=logs, stderr=logs,
                ))
                children.append(subprocess.Popen(
                    [node, str(GATEWAY)],
                    cwd=ROOT, env=env, stdout=logs, stderr=logs,
                ))

                wait_until_ready(base_url, children)

                public_client = make_opener()
                owner_client = make_opener()
                other_client = make_opener()

                owner_csrf = login(
                    owner_client, base_url, "bl17-benchmark-owner"
                )
                other_csrf = login(
                    other_client, base_url, "bl17-benchmark-other"
                )

                list_url = urljoin(base_url, "/api/events")
                detail_url = urljoin(
                    base_url, f"/api/events/{FIRST_EVENT_ID}"
                )
                register_url = urljoin(
                    base_url, f"/api/events/{FIRST_EVENT_ID}/register"
                )
                edit_url = urljoin(
                    base_url, f"/api/events/{FIRST_EVENT_ID}"
                )

                # Warm-up requests are not included in reported samples.
                for url in (list_url, detail_url):
                    status, _, _ = request_json(public_client, url)
                    if status != 200:
                        raise RuntimeError(
                            f"Warm-up request failed: {url} -> {status}"
                        )

                list_samples = []
                detail_samples = []
                registration_samples = []
                edit_denial_samples = []
                delete_denial_samples = []

                for _ in range(args.iterations):
                    status, payload, elapsed = request_json(
                        public_client, list_url
                    )
                    if status != 200:
                        raise RuntimeError(f"Event list returned HTTP {status}")
                    if len(payload.get("events", [])) != args.events:
                        raise RuntimeError("Event list fixture count was unexpected.")
                    list_samples.append(elapsed)

                    status, payload, elapsed = request_json(
                        public_client, detail_url
                    )
                    if status != 200 or "event" not in payload:
                        raise RuntimeError(f"Event details returned HTTP {status}")
                    detail_samples.append(elapsed)

                    # Unique synthetic email for each committed registration.
                    status, _, elapsed = request_json(
                        public_client,
                        register_url,
                        method="POST",
                        body={
                            "name": f"BL17 Synthetic Attendee {_}",
                            "email": f"bl17-benchmark-{_}@example.com",
                        },
                    )
                    if status != 201:
                        raise RuntimeError(
                            f"Registration returned HTTP {status}; "
                            "check route and fixture setup."
                        )
                    registration_samples.append(elapsed)

                    # Non-owner edit must be forbidden without changing data.
                    status, _, elapsed = request_json(
                        other_client,
                        edit_url,
                        method="PUT",
                        body={
                            "name": "Unauthorized synthetic edit",
                            "description": "Must not be saved",
                            "date": (date.today() + timedelta(days=30)).isoformat(),
                            "time": "11:00:00",
                            "location": "Synthetic Test Hall",
                        },
                        headers={"X-CSRFToken": other_csrf},
                    )
                    if status != 403:
                        raise RuntimeError(
                            f"Non-owner edit expected HTTP 403, got {status}."
                        )
                    edit_denial_samples.append(elapsed)

                    # Non-owner delete must be forbidden as well.
                    status, _, elapsed = request_json(
                        other_client,
                        edit_url,
                        method="DELETE",
                        body={},
                        headers={"X-CSRFToken": other_csrf},
                    )
                    if status != 403:
                        raise RuntimeError(
                            f"Non-owner delete expected HTTP 403, got {status}."
                        )
                    delete_denial_samples.append(elapsed)

                results = {
                    "metadata": {
                        "issue": "BL-17",
                        "measured_at_local": now,
                        "platform": sys.platform,
                        "python": sys.version.split()[0],
                        "node": subprocess.run(
                            [node, "--version"],
                            check=True, capture_output=True, text=True,
                        ).stdout.strip(),
                        "database": "temporary SQLite database",
                        "route": "Node gateway -> Django -> SQLite",
                        "synthetic_event_count": args.events,
                        "iterations_per_action": args.iterations,
                        "warmup_requests": 1,
                        "measurement": (
                            "Client-side elapsed time for each HTTP request "
                            "through the gateway, measured with time.perf_counter."
                        ),
                        "not_measured": [
                            "Browser rendering and action-to-visible-result time",
                            "Production traffic or production database performance",
                            "Browser network throttling or remote-network latency",
                        ],
                    },
                    "results": {
                        "event_list_api": summarize(list_samples),
                        "event_details_api": summarize(detail_samples),
                        "registration_api": summarize(registration_samples),
                        "nonowner_edit_denial_api": summarize(edit_denial_samples),
                        "nonowner_delete_denial_api": summarize(delete_denial_samples),
                    },
                }

            except Exception:
                logs.seek(0)
                print(logs.read()[-6000:], file=sys.stderr)
                raise
            finally:
                for child in children:
                    if child.poll() is None:
                        child.terminate()
                for child in children:
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(results, indent=2) + "\n",
        encoding="utf-8",
    )

    print("BL-17 API benchmark complete.")
    print(f"Events: {args.events}; measured iterations: {args.iterations}")
    print(f"Report: {output.relative_to(ROOT)}")
    for action, values in results["results"].items():
        print(
            f"{action}: median={values['median_ms']:.3f} ms, "
            f"p95={values['p95_ms']:.3f} ms, "
            f"n={values['samples']}"
        )
    print("API timings only; browser-visible timing was not measured.")


if __name__ == "__main__":
    main()

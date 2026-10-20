"""Verify a fresh local database and the React -> Node -> Django connection."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_json(url, children):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            raise RuntimeError("A development service exited before it became ready.")
        try:
            with urlopen(url, timeout=1) as response:
                data = json.load(response)
            if data.get("status") == "ok" and data.get("database") == "ok":
                return data
        except (URLError, OSError, ValueError):
            pass
        time.sleep(0.1)
    raise RuntimeError("The local application did not become ready within 20 seconds.")


def main():
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required.")
    ports = set()
    while len(ports) < 3:
        ports.add(free_port())
    backend_port, gateway_port, frontend_port = ports
    children = []
    with tempfile.TemporaryDirectory(prefix="ems-smoke-") as temporary:
        env = {
            **os.environ, "EMS_DEBUG": "1",
            "EMS_DB_PATH": str(Path(temporary) / "smoke.sqlite3"),
            "DJANGO_UPSTREAM": f"http://127.0.0.1:{backend_port}",
            "GATEWAY_PORT": str(gateway_port),
        }
        hidden = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
            try:
                for command in [
                    [sys.executable, "backend/manage.py", "migrate", "--noinput"],
                    [sys.executable, "backend/manage.py", "seed_demo"],
                ]:
                    subprocess.run(
                        command, cwd=ROOT, env=env, check=True, stdout=log,
                        stderr=log, timeout=45, **hidden,
                    )
                for command in [
                    [sys.executable, "backend/manage.py", "runserver",
                     f"127.0.0.1:{backend_port}", "--noreload"],
                    [node, "gateway/server.mjs"],
                    [node, "node_modules/vite/bin/vite.js", "--config",
                     "frontend/vite.config.mjs", "--port", str(frontend_port), "--strictPort"],
                ]:
                    children.append(subprocess.Popen(
                        command, cwd=ROOT, env=env, stdout=log, stderr=log, **hidden
                    ))
                result = wait_json(f"http://127.0.0.1:{frontend_port}/api/health", children)
                with urlopen(f"http://127.0.0.1:{frontend_port}", timeout=3) as response:
                    assert '<div id="root"></div>' in response.read().decode()
                print("PASS: fresh migrations and synthetic fixtures.")
                print("PASS: frontend dev server -> Node gateway -> Django -> SQLite:", result)
            except Exception:
                log.seek(0)
                print(log.read()[-4000:], file=sys.stderr)
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


if __name__ == "__main__":
    main()

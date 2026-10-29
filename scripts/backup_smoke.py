"""Verify scheduled backups/restores with canonical models and no feature servers."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

from db_backup import inspect_database, restore, verify

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="ems-canonical-backup-") as temporary:
        directory = Path(temporary)
        source = directory / "source.sqlite3"
        snapshots = directory / "backups"
        env = {**os.environ, "EMS_DB_PATH": str(source), "EMS_DEBUG": "1",
               "EMS_SECRET_KEY": secrets.token_urlsafe(40),
               "EMS_DEMO_PASSWORD": secrets.token_urlsafe(24)}
        hidden = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        for command in ("migrate", "seed_demo"):
            subprocess.run([sys.executable, "backend/manage.py", command], cwd=ROOT,
                           env=env, check=True, capture_output=True, timeout=60, **hidden)
        expected = {"organizers": 2, "events": 2, "registrations": 1}
        assert inspect_database(source) == expected
        worker = subprocess.Popen([sys.executable, "scripts/db_backup.py", "run",
            "--directory", str(snapshots), "--interval", "1"], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **hidden)
        try:
            deadline = time.monotonic() + 15
            while len(list(snapshots.glob("events-*.json"))) < 2:
                if worker.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("The scheduled backup worker did not create two snapshots.")
                time.sleep(0.1)
        finally:
            worker.terminate()
            worker.wait(timeout=10)
        snapshot = sorted(snapshots.glob("events-*.sqlite3"))[-1]
        assert verify(snapshot)["counts"] == expected
        restore(snapshot, directory / "isolated" / "restore.sqlite3", source)
        assert inspect_database(source) == expected
        print("PASS: canonical migrations and direct synthetic seeding without feature servers.")
        print("PASS: two scheduled snapshots; checksum, counts and foreign keys verified.")
        print("PASS: isolated restore verified; original database unchanged.")


if __name__ == "__main__":
    main()

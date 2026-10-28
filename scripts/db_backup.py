"""SQLite online backups, freshness checks and isolated restores.

Never copy a live SQLite file directly. Backup API snapshots include committed WAL
data. All output is operational metadata; records and credentials are not logged.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
TABLES = ("organizers", "events", "registrations")


def connect_readonly(path):
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)


def inspect_database(path):
    with closing(connect_readonly(path)) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Database integrity check failed.")
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Database relationship check failed.")
        return {table: db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                for table in TABLES}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, data):
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            os.chmod(temporary, 0o600)
            json.dump(data, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def verify(snapshot):
    snapshot = Path(snapshot)
    metadata = json.loads(snapshot.with_suffix(".json").read_text(encoding="utf-8"))
    if metadata["sha256"] != digest(snapshot):
        raise ValueError("Backup checksum mismatch.")
    if metadata["counts"] != inspect_database(snapshot):
        raise ValueError("Backup record counts do not match its manifest.")
    return metadata


def backup(source, directory, retain=7):
    source, directory = Path(source).resolve(), Path(directory).resolve()
    if not source.is_file():
        raise ValueError("Source database does not exist.")
    if retain < 1:
        raise ValueError("Retain at least one backup.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        os.chmod(directory, 0o700)
    stamp = datetime.now(timezone.utc)
    snapshot = directory / ("events-" + stamp.strftime("%Y%m%dT%H%M%S%fZ-")
                            + uuid.uuid4().hex[:8] + ".sqlite3")
    temporary = snapshot.with_suffix(".partial")
    try:
        # Pre-create privately before SQLite opens the output.
        with temporary.open("xb"):
            os.chmod(temporary, 0o600)
        with closing(connect_readonly(source)) as src, closing(sqlite3.connect(temporary)) as dst:
            deadline = time.monotonic() + 60

            def progress(*_):
                if time.monotonic() > deadline:
                    raise TimeoutError("Backup could not finish within 60 seconds.")

            src.backup(dst, pages=256, progress=progress, sleep=0.05)
        counts = inspect_database(temporary)
        with temporary.open("r+b") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, snapshot)
        metadata = {"created_at": stamp.isoformat(), "sha256": digest(snapshot),
                    "counts": counts, "format": 1}
        write_json(snapshot.with_suffix(".json"), metadata)
        verify(snapshot)
        # Only completed, verified pairs qualify for pruning; never touch other files.
        completed = []
        for candidate in sorted(directory.glob("events-*.sqlite3"), reverse=True):
            try:
                verify(candidate)
                completed.append(candidate)
            except (ValueError, OSError, sqlite3.Error, KeyError):
                # Preserve damaged/unpaired files for investigation. They must
                # neither displace valid restore points nor prevent new backups.
                continue
        for old in completed[retain:]:
            if old != snapshot and old.with_suffix(".json").is_file():
                old.unlink()
                old.with_suffix(".json").unlink()
        (directory / "last-failure.json").unlink(missing_ok=True)
        return snapshot
    finally:
        temporary.unlink(missing_ok=True)


def restore(snapshot, destination, source):
    """Restore into a NEW path, never over the working database or a backup."""
    snapshot, destination, source = map(lambda p: Path(p).resolve(),
                                        (snapshot, destination, source))
    if destination in (source, snapshot) or destination.parent == snapshot.parent:
        raise ValueError("Restore must use a separate location from live data and backups.")
    metadata = verify(snapshot)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental overwrite, including concurrent restores.
    with destination.open("xb"):
        os.chmod(destination, 0o600)
    try:
        with closing(connect_readonly(snapshot)) as src, closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
        if inspect_database(destination) != metadata["counts"]:
            raise ValueError("Restored record counts do not match the backup.")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return metadata


def status(directory, max_age=24 * 3600, now=None):
    directory = Path(directory)
    if (directory / "last-failure.json").exists():
        raise ValueError("The latest scheduled backup attempt failed.")
    completed = sorted(directory.glob("events-*.sqlite3"), reverse=True)
    if not completed:
        raise ValueError("No completed backup is available.")
    metadata = verify(completed[0])
    age = ((now or datetime.now(timezone.utc))
           - datetime.fromisoformat(metadata["created_at"])).total_seconds()
    if age < -300 or age > max_age:
        raise ValueError("The newest backup is stale or has an invalid timestamp.")
    return {"status": "ok", "age_seconds": round(age),
            "backup": completed[0].name}


def run_due(source, directory, interval=23 * 3600, retain=7):
    if not 1 <= interval <= 23 * 3600:
        raise ValueError("Backup interval must be between 1 second and 23 hours.")
    try:
        status(directory, max_age=interval)
        return False
    except (ValueError, OSError, sqlite3.Error, KeyError, json.JSONDecodeError):
        try:
            backup(source, directory, retain)
        except Exception:
            Path(directory).mkdir(parents=True, exist_ok=True, mode=0o700)
            write_json(Path(directory) / "last-failure.json",
                       {"failed_at": datetime.now(timezone.utc).isoformat()})
            raise
        return True


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "verify", "restore", "status", "run"])
    parser.add_argument("--database", type=Path, default=Path(os.getenv("EMS_DB_PATH", "data/events.sqlite3")))
    parser.add_argument("--directory", type=Path, default=Path(os.getenv("EMS_BACKUP_DIR", "backups")))
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--retain", type=int, default=7)
    parser.add_argument("--interval", type=int, default=23 * 3600)
    args = parser.parse_args()
    if not args.database.is_absolute():
        args.database = ROOT / args.database
    if not args.directory.is_absolute():
        args.directory = ROOT / args.directory
    if args.action in ("verify", "restore") and args.snapshot is None:
        parser.error("--snapshot is required")
    if args.action == "restore" and args.destination is None:
        parser.error("--destination is required")
    if args.action == "run" and not 1 <= args.interval <= 23 * 3600:
        parser.error("--interval must be between 1 and 82800 seconds")
    try:
        if args.action == "backup":
            print(json.dumps({"status": "ok", "backup": backup(args.database, args.directory, args.retain).name}))
        elif args.action == "verify":
            verify(args.snapshot)
            print('{"status": "ok", "verified": true}')
        elif args.action == "restore":
            restore(args.snapshot, args.destination, args.database)
            print('{"status": "ok", "restored": true}')
        elif args.action == "status":
            print(json.dumps(status(args.directory)))
        else:
            while True:
                try:
                    changed = run_due(args.database, args.directory, args.interval, args.retain)
                    print(json.dumps({"status": "ok", "backup_created": changed}), flush=True)
                except (ValueError, OSError, sqlite3.Error):
                    print('{"status": "failed", "message": "Backup failed; check storage and database access."}', flush=True)
                time.sleep(min(60, args.interval))
    except (ValueError, OSError, sqlite3.Error, KeyError):
        print('{"status": "failed", "message": "Operation failed; check paths, manifest, storage and database integrity."}', file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

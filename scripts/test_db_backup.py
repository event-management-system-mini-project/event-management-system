"""Exercise the actual backup scheduler and restore against disposable databases."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from db_backup import backup, inspect_database, restore, run_due, status, verify


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "live.sqlite3"
        self.directory = self.root / "backups"
        with closing(sqlite3.connect(self.source)) as db:
            db.executescript('''
                PRAGMA foreign_keys=ON;
                CREATE TABLE organizers(id TEXT PRIMARY KEY);
                CREATE TABLE events(id TEXT PRIMARY KEY, organizer_id TEXT REFERENCES organizers(id));
                CREATE TABLE registrations(id TEXT PRIMARY KEY, event_id TEXT REFERENCES events(id));
                INSERT INTO organizers VALUES ('synthetic-owner');
                INSERT INTO events VALUES ('synthetic-event', 'synthetic-owner');
                INSERT INTO registrations VALUES ('synthetic-registration', 'synthetic-event');
            ''')

    def test_online_snapshot_includes_committed_wal_and_excludes_pending_writes(self):
        with closing(sqlite3.connect(self.source)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("INSERT INTO organizers VALUES ('committed')")
            writer.commit()
            writer.execute("INSERT INTO organizers VALUES ('uncommitted')")
            snap = backup(self.source, self.directory)
            self.assertEqual(verify(snap)["counts"]["organizers"], 2)
            writer.rollback()
        target = self.root / "restore" / "isolated.sqlite3"
        restore(snap, target, self.source)
        self.assertEqual(inspect_database(target), verify(snap)["counts"])
        self.assertEqual(inspect_database(self.source)["organizers"], 2)

    def test_restore_never_overwrites_live_existing_or_backup_paths(self):
        snap = backup(self.source, self.directory)
        for target in (self.source, snap, self.directory / "other.sqlite3"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                restore(snap, target, self.source)
        target = self.root / "existing.sqlite3"
        target.write_text("keep me")
        with self.assertRaises(FileExistsError):
            restore(snap, target, self.source)
        self.assertEqual(target.read_text(), "keep me")

    def test_corrupt_snapshot_is_rejected_before_restore(self):
        snap = backup(self.source, self.directory)
        with snap.open("ab") as stream:
            stream.write(b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum"):
            restore(snap, self.root / "restored.sqlite3", self.source)
        self.assertFalse((self.root / "restored.sqlite3").exists())

    def test_retention_only_removes_old_completed_pairs(self):
        for _ in range(3):
            backup(self.source, self.directory, retain=2)
        self.assertEqual(len(list(self.directory.glob("*.sqlite3"))), 2)
        self.assertEqual(len(list(self.directory.glob("events-*.json"))), 2)
        self.assertFalse(list(self.directory.glob("*.partial")))

    def test_missing_database_is_not_created_and_failed_schedule_is_unhealthy(self):
        missing = self.root / "missing.sqlite3"
        with self.assertRaises(ValueError):
            run_due(missing, self.directory)
        self.assertFalse(missing.exists())
        self.assertTrue((self.directory / "last-failure.json").exists())
        with self.assertRaisesRegex(ValueError, "failed"):
            status(self.directory)
        self.assertTrue(run_due(self.source, self.directory))
        self.assertEqual(status(self.directory)["status"], "ok")

    def test_schedule_creates_initial_skips_fresh_and_replaces_stale_snapshot(self):
        self.assertTrue(run_due(self.source, self.directory))
        self.assertFalse(run_due(self.source, self.directory))
        future = datetime.now(timezone.utc) + timedelta(hours=25)
        with self.assertRaisesRegex(ValueError, "stale"):
            status(self.directory, now=future)
        # A controlled clock drives the real due-selection path without waiting a day.
        with patch("db_backup.datetime") as clock:
            clock.now.return_value = future
            clock.fromisoformat.side_effect = datetime.fromisoformat
            self.assertTrue(run_due(self.source, self.directory))
        self.assertEqual(len(list(self.directory.glob("*.sqlite3"))), 2)
        for interval in (0, 24 * 3600):
            with self.assertRaises(ValueError):
                run_due(self.source, self.directory, interval=interval)

    def test_foreign_key_corruption_rejects_backup(self):
        with closing(sqlite3.connect(self.source)) as db:
            db.execute("INSERT INTO registrations VALUES ('orphan', 'missing')")
            db.commit()
        with self.assertRaisesRegex(ValueError, "relationship"):
            backup(self.source, self.directory)
        self.assertFalse(list(self.directory.glob("*.sqlite3")))

    def test_failed_snapshot_does_not_remove_previous_backup(self):
        snap = backup(self.source, self.directory)
        with patch("db_backup.inspect_database", side_effect=ValueError("disk failure")):
            with self.assertRaises(ValueError):
                backup(self.source, self.directory)
        verify(snap)
        self.assertFalse(list(self.directory.glob("*.partial")))


if __name__ == "__main__":
    unittest.main()

"""Backup and restore: the WAL-safety, rotation, and round-trip
guarantees added after the April 2026 corruption incident."""

import sqlite3
import threading
import time
import zipfile

from database import Database


def test_backup_captures_uncheckpointed_wal_writes(db, tmp_path):
    """The bug that motivated the backup rewrite: writes still in the
    -wal sidecar must appear in the backup zip."""
    db.add_tag("wal-resident-tag")  # committed, but likely not checkpointed

    zip_path = str(tmp_path / "backup.zip")
    db.create_full_backup(zip_path, include_images=False)

    extract_dir = tmp_path / "extracted"
    with zipfile.ZipFile(zip_path) as zf:
        zf.extract("tarot_journal.db", extract_dir)
    conn = sqlite3.connect(str(extract_dir / "tarot_journal.db"))
    count = conn.execute(
        "SELECT COUNT(*) FROM tags WHERE name='wal-resident-tag'").fetchone()[0]
    conn.close()
    assert count == 1


def test_auto_backup_rotation_keeps_newest(db, tmp_path):
    backup_dir = str(tmp_path / "auto")
    for _ in range(5):
        time.sleep(1.05)  # snapshot names are timestamped to the second
        db.auto_backup(backup_dir, keep=3)
    snapshots = sorted((tmp_path / "auto").glob("tarot_journal_auto_*.db"))
    assert len(snapshots) == 3


def test_backup_restore_round_trip(db, tmp_path):
    """Data added after a backup disappears on restore; data from
    before the backup survives. The single most important test in
    the suite."""
    db.add_tag("before-backup")
    zip_path = str(tmp_path / "roundtrip.zip")
    db.create_full_backup(zip_path, include_images=False)

    db.add_tag("after-backup")
    result = db.restore_from_backup(zip_path)

    tags = [t["name"] for t in db.get_tags()]
    assert "before-backup" in tags
    assert "after-backup" not in tags
    assert result["backup_date"] != "Unknown"

    integrity = db.conn.execute("PRAGMA integrity_check").fetchone()[0]
    assert integrity == "ok"


def test_restore_survives_concurrent_readers(db, tmp_path):
    """Threads querying throughout a restore must never see a
    half-copied database file (the corruption scenario db_swap_guard
    exists to prevent)."""
    db.add_tag("keep")
    zip_path = str(tmp_path / "concurrent.zip")
    db.create_full_backup(zip_path, include_images=False)

    corruption = []
    stop = threading.Event()

    def hammer():
        while not stop.is_set():
            try:
                db.get_tags()
            except sqlite3.DatabaseError as e:
                msg = str(e).lower()
                if "malformed" in msg or "not a database" in msg:
                    corruption.append(str(e))
            except Exception:
                pass  # transient closed-connection races are expected
            time.sleep(0.001)

    threads = [threading.Thread(target=hammer) for _ in range(4)]
    for t in threads:
        t.start()
    try:
        time.sleep(0.1)
        db.restore_from_backup(zip_path)
        time.sleep(0.2)
    finally:
        stop.set()
        for t in threads:
            t.join()

    assert corruption == []
    assert db.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_backup_endpoint_leaves_no_temp_files(client, tmp_path):
    """The /api/backup route writes straight to the destination folder
    and must leave nothing behind in the system temp dir (regression
    test for the old streaming flow's temp-zip leak)."""
    import glob
    import os
    import tempfile

    before = set(glob.glob(os.path.join(tempfile.gettempdir(), "tarot_backup_*")))
    resp = client.post("/api/backup", json={
        "include_images": False,
        "dest_dir": str(tmp_path),
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert os.path.dirname(body["path"]) == str(tmp_path)
    assert body["bytes"] > 1000
    after = set(glob.glob(os.path.join(tempfile.gettempdir(), "tarot_backup_*")))
    assert after - before == set()

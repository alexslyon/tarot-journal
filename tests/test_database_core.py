"""Core database behavior: schema creation, migration idempotence,
and the atomicity guarantees the entry editor relies on."""

import pytest

from database import Database


def test_fresh_database_creates_and_seeds(db):
    """A brand-new database initializes with seeded cartomancy types."""
    types = [t["name"] for t in db.get_cartomancy_types()]
    assert any(t.lower() == "tarot" for t in types)


def test_reopening_database_is_idempotent(tmp_path):
    """Opening the same file twice re-runs every startup migration.
    This must be a clean no-op — a migration that isn't re-runnable
    bricks the app on its second launch."""
    path = str(tmp_path / "reopen.db")
    first = Database(db_path=path)
    tag_id = first.add_tag("survives-reopen")
    first.close()

    second = Database(db_path=path)
    tags = [t["name"] for t in second.get_tags()]
    assert "survives-reopen" in tags
    second.close()


def test_replace_entry_readings_swaps_atomically(db):
    entry_id = db.add_entry(title="Atomic test")
    db.add_entry_reading(entry_id, spread_name="Original",
                         cards_used=[{"name": "The Tower"}], position_order=0)

    ids = db.replace_entry_readings(entry_id, [
        {"spread_name": "New A", "cards_used": [{"name": "The Star"}]},
        {"spread_name": "New B", "cards_used": [{"name": "The Moon"}]},
    ])
    rows = db.get_entry_readings(entry_id)
    assert [r["spread_name"] for r in rows] == ["New A", "New B"]
    assert len(ids) == 2


def test_replace_entry_readings_failure_preserves_originals(db):
    """A save that fails partway must leave the entry's original
    readings untouched — this is the app's core data-loss guarantee."""
    entry_id = db.add_entry(title="Rollback test")
    db.replace_entry_readings(entry_id, [
        {"spread_name": "Keep me", "cards_used": [{"name": "The Sun"}]},
    ])

    class Unserializable:
        pass

    with pytest.raises(TypeError):
        db.replace_entry_readings(entry_id, [
            {"spread_name": "half", "cards_used": [{"name": "ok"}]},
            {"spread_name": "boom", "cards_used": [Unserializable()]},
        ])

    rows = db.get_entry_readings(entry_id)
    assert [r["spread_name"] for r in rows] == ["Keep me"]

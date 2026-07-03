"""Startup migrations against legacy data shapes."""

from conftest import make_deck_with_card

from database.correspondence_migration import run_correspondence_migration


def _clear_migration_flag(db):
    db.conn.execute(
        "UPDATE settings SET value='' WHERE key='correspondence_migration_done'")
    db.conn.commit()


def test_correspondence_migration_handles_legacy_fields(db):
    """Opening a pre-migration database (e.g. a restored old backup)
    with legacy Astrology/Element custom fields must migrate them, not
    crash at startup (regression test for the ON CONFLICT mismatch)."""
    _, card_id = make_deck_with_card(db)
    for name, value in (("Element", "Fire"), ("Astrology", "Aries")):
        db.conn.execute(
            "INSERT INTO card_custom_fields (card_id, field_name, field_value, field_type)"
            " VALUES (?, ?, ?, 'text')",
            (card_id, name, value))
    db.conn.commit()

    _clear_migration_flag(db)
    run_correspondence_migration(db)

    rows = {(r["field_name"], r["field_value"]) for r in db.conn.execute(
        "SELECT field_name, field_value FROM card_correspondence_overrides"
        " WHERE card_id=?", (card_id,)).fetchall()}
    assert ("element", "Fire") in rows
    assert ("zodiac_sign", "Aries") in rows

    # Re-running (e.g. flag lost) must not error or duplicate rows.
    count_before = len(rows)
    _clear_migration_flag(db)
    run_correspondence_migration(db)
    count_after = db.conn.execute(
        "SELECT COUNT(*) FROM card_correspondence_overrides WHERE card_id=?",
        (card_id,)).fetchone()[0]
    assert count_after == count_before

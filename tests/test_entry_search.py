"""Entry search filters: querent and date-range behavior."""


def test_search_by_querent(db):
    alice = db.add_profile("Alice")
    bob = db.add_profile("Bob")
    e1 = db.add_entry(title="Alice's reading")
    e2 = db.add_entry(title="Bob's reading")
    db.set_entry_querents(e1, [alice])
    db.set_entry_querents(e2, [bob])

    results = db.search_entries(querent_id=alice)
    titles = [r["title"] for r in results]
    assert titles == ["Alice's reading"]


def test_date_to_includes_the_end_date(db):
    """Regression: `<= date_to` string-compare excluded everything on
    the end date itself, because '2026-07-02T10:00' sorts after
    '2026-07-02'."""
    db.add_entry(title="on the end date", reading_datetime="2026-07-02T10:00:00")
    db.add_entry(title="day after", reading_datetime="2026-07-03T09:00:00")

    results = db.search_entries(date_from="2026-07-01", date_to="2026-07-02")
    titles = [r["title"] for r in results]
    assert titles == ["on the end date"]


def test_date_filter_uses_reading_datetime_not_created_at(db):
    """An entry logged today about a reading last month must match a
    search for last month's dates."""
    db.add_entry(title="backdated reading", reading_datetime="2026-06-01T20:00:00")

    results = db.search_entries(date_from="2026-05-30", date_to="2026-06-02")
    assert [r["title"] for r in results] == ["backdated reading"]
    # ...and not match a search for the (current) creation date window
    results_now = db.search_entries(date_from="2026-07-01", date_to="2026-12-31")
    assert "backdated reading" not in [r["title"] for r in results_now]

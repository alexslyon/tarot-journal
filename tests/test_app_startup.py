"""App factory behavior: data-dir resolution and the one-time
migration of the database out of the repo root."""

import os

import pytest

import backend.app as appmod
from database import Database


@pytest.fixture
def isolated_dirs(tmp_path, monkeypatch):
    """Fake repo root + app-data dir so create_app never touches the
    real project folder or ~/Library."""
    fake_repo = tmp_path / "repo"
    data_dir = tmp_path / "appdata"
    fake_repo.mkdir()
    monkeypatch.setenv("TAROT_JOURNAL_DATA_DIR", str(data_dir))
    monkeypatch.setattr(appmod, "PROJECT_ROOT", str(fake_repo))
    return fake_repo, data_dir


def test_fresh_start_creates_db_in_data_dir(isolated_dirs):
    fake_repo, data_dir = isolated_dirs
    app = appmod.create_app()
    db = app.config['DB']
    try:
        assert db.db_path == str(data_dir / "tarot_journal.db")
        assert os.path.exists(db.db_path)
    finally:
        db.close()


def test_legacy_db_migrates_from_repo_root(isolated_dirs):
    fake_repo, data_dir = isolated_dirs

    legacy = Database(db_path=str(fake_repo / "tarot_journal.db"))
    legacy.add_tag("moved-with-me")
    legacy.close()

    app = appmod.create_app()
    db = app.config['DB']
    try:
        assert "moved-with-me" in [t["name"] for t in db.get_tags()]
        assert not os.path.exists(fake_repo / "tarot_journal.db")
        # launch snapshot landed in the new backups home
        autos = os.listdir(data_dir / "backups" / "auto")
        assert any(a.startswith("tarot_journal_auto_") for a in autos)
    finally:
        db.close()


def test_existing_data_dir_db_wins_over_legacy(isolated_dirs):
    """If databases exist in BOTH locations, the app-data one is used
    and the legacy file is left untouched (never overwritten)."""
    fake_repo, data_dir = isolated_dirs
    data_dir.mkdir()  # normally created by create_app itself

    current = Database(db_path=str(data_dir / "tarot_journal.db"))
    current.add_tag("i-am-current")
    current.close()

    legacy = Database(db_path=str(fake_repo / "tarot_journal.db"))
    legacy.add_tag("i-am-legacy")
    legacy.close()

    app = appmod.create_app()
    db = app.config['DB']
    try:
        tags = [t["name"] for t in db.get_tags()]
        assert "i-am-current" in tags
        assert "i-am-legacy" not in tags
        assert os.path.exists(fake_repo / "tarot_journal.db")
    finally:
        db.close()

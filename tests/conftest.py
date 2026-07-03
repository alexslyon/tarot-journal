"""Shared fixtures for the backend test suite.

Every fixture works on throwaway databases under pytest's tmp_path —
tests never touch the real journal database or app-data folder.
"""

import os
import sys

import pytest

# Make the project root importable (database/, backend/, root helpers)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import Database  # noqa: E402


@pytest.fixture
def db(tmp_path):
    """A fresh Database on a throwaway file (runs full schema + seeds)."""
    database = Database(db_path=str(tmp_path / "test.db"))
    yield database
    database.close()


@pytest.fixture
def flask_app(db):
    """A Flask app wired to the throwaway database (no startup side
    effects like the legacy-location migration or auto-backup)."""
    from flask import Flask
    from backend.routes import register_blueprints

    app = Flask(__name__)
    app.config['DB'] = db
    register_blueprints(app)
    return app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


def make_deck_with_card(db, deck_name="Test Deck", card_name="The Fool"):
    """Helper: create a tarot deck containing one card."""
    tarot = next(t for t in db.get_cartomancy_types() if t["name"].lower() == "tarot")
    deck_id = db.add_deck(deck_name, type_ids=[tarot["id"]])
    card_id = db.add_card(deck_id, card_name)
    return deck_id, card_id

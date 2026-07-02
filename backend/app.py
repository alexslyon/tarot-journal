"""
Flask application factory for the Tarot Journal API.

Creates a Flask app that wraps the existing database.py data layer,
serving all data over a REST API for the React frontend.
"""

import sys
import os
import atexit

# Add the project root to Python path so we can import database.py, etc.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, send_from_directory
from flask_cors import CORS

from backend.config import CORS_ORIGINS

# Path to the built React frontend
FRONTEND_DIST = os.path.join(PROJECT_ROOT, 'frontend', 'dist')


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder=None)

    # Allow the React dev server to make requests
    CORS(app, origins=CORS_ORIGINS)

    # Import here to avoid circular imports and ensure PROJECT_ROOT is on path
    from database import Database
    from thumbnail_cache import get_cache
    from theme_config import get_theme

    # Use absolute path so Flask works regardless of working directory
    db_path = os.path.join(PROJECT_ROOT, 'tarot_journal.db')
    db = Database(db_path=db_path)
    app.config['DB'] = db

    # Automatic safety net: snapshot the database on every launch,
    # keeping the 10 most recent snapshots in backups/auto/. This
    # protects against corruption or accidental data loss even if the
    # user never presses the manual Backup button. A failed snapshot
    # must never prevent the app from starting, hence the broad catch.
    try:
        db.auto_backup(os.path.join(PROJECT_ROOT, 'backups', 'auto'), keep=10)
    except Exception as e:
        from logger_config import get_logger
        get_logger('backend').warning("Automatic startup backup failed: %s", e)
    app.config['THUMB_CACHE'] = get_cache()
    app.config['THEME'] = get_theme()

    # Ensure the database is properly closed (and WAL checkpointed) on exit
    atexit.register(db.close)

    # Register route blueprints
    from backend.routes import register_blueprints
    register_blueprints(app)

    # Serve the built React frontend (production mode)
    if os.path.isdir(FRONTEND_DIST):
        @app.route('/')
        def serve_index():
            return send_from_directory(FRONTEND_DIST, 'index.html')

        @app.route('/assets/<path:filename>')
        def serve_assets(filename):
            return send_from_directory(os.path.join(FRONTEND_DIST, 'assets'), filename)

        # SPA fallback: serve index.html for any non-API, non-file routes
        @app.errorhandler(404)
        def spa_fallback(e):
            # Only serve SPA for non-API routes
            from flask import request
            if request.path.startswith('/api/'):
                return {'error': 'Not found'}, 404
            return send_from_directory(FRONTEND_DIST, 'index.html')

    return app

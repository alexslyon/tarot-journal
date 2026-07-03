"""
Backend configuration for the Flask API server.
"""

import os
import sys

# The project root is one level up from this file's directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir() -> str:
    """Directory for user data (database + backups), outside the repo.

    Keeping the journal database in the code folder meant it sat next
    to git operations, editor tooling, and stray backup copies — risky
    company for the app's most important file. The platform-standard
    app-data folder is calmer territory. The TAROT_JOURNAL_DATA_DIR
    env var overrides it (used by tests).
    """
    override = os.environ.get('TAROT_JOURNAL_DATA_DIR')
    if override:
        return override
    if sys.platform == 'darwin':
        return os.path.expanduser('~/Library/Application Support/TarotJournal')
    return os.path.expanduser('~/.tarot_journal')

# Flask server port
PORT = int(os.environ.get('FLASK_PORT', 5678))

# CORS origins allowed (Vite dev server)
CORS_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

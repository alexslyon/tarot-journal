"""
Entry point for the Flask development server.

Usage:
    python backend/run.py
"""

import sys
import os

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app import create_app
from backend.config import PORT

app = create_app()

if __name__ == '__main__':
    print(f"Starting Tarot Journal API on http://localhost:{PORT}")
    app.run(host='127.0.0.1', port=PORT, debug=True)

"""
Backend configuration for the Flask API server.
"""

import os

# The project root is one level up from this file's directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Flask server port
PORT = int(os.environ.get('FLASK_PORT', 5678))

# CORS origins allowed (Vite dev server)
CORS_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

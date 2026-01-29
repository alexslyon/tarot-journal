"""
Application configuration for Tarot Journal.

Stores user-customizable settings like window size, image dimensions,
and file paths. Reads from app_config.json if it exists; otherwise
uses built-in defaults. The config file is only created when you
explicitly save changes (e.g., from a settings UI).

To customize, create app_config.json next to this file with any
values you want to override. You only need to include the values
you want to change — missing values use defaults.

Example app_config.json:
{
    "window": {
        "max_width": 900
    }
}
"""

import os
from pathlib import Path

from config_base import JsonConfig


DEFAULTS = {
    # Main window dimensions
    "window": {
        "max_width": 1200,          # Maximum window width in pixels
        "max_height": 800,          # Maximum window height in pixels
        "screen_percent": 0.85,     # Use this % of screen if smaller than max
    },

    # Panel splitter positions (width of left panel in pixels)
    "panels": {
        "journal_splitter": 300,    # Journal entries list width
        "cards_splitter": 280,      # Deck list width
        "spreads_splitter": 250,    # Spreads list width
    },

    # Image display sizes [width, height] in pixels
    "images": {
        "card_info_max": [300, 450],       # Card detail view
        "card_edit_max": [300, 450],       # Card edit dialog
        "card_gallery_max": [200, 300],    # Card gallery thumbnails
        "deck_back_max": [100, 150],       # Deck card-back in list
        "deck_back_preview_max": [150, 225],  # Card-back preview in settings
        "thumbnail_size": [300, 450],      # Cached thumbnail size
        "preview_size": [500, 750],        # Larger preview size
    },

    # File paths (relative to app directory)
    "paths": {
        "database": "tarot_journal.db",
        "thumbnail_cache_dir": ".thumbnail_cache",
    },

    # Logging settings
    "logging": {
        "max_bytes": 1_000_000,     # Max log file size (1 MB)
        "backup_count": 3,          # Number of old log files to keep
    },
}

_CONFIG_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "app_config.json"


class AppConfig(JsonConfig):
    """Loads and provides access to app configuration."""

    DEFAULTS = DEFAULTS

    def __init__(self, config_file: Path = None):
        super().__init__(config_file or _CONFIG_FILE, merge_mode='deep')


# Global singleton
_instance = None


def get_config() -> AppConfig:
    """Get the global app config instance."""
    global _instance
    if _instance is None:
        _instance = AppConfig()
    return _instance

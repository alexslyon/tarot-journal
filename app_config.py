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

import json
import os
from pathlib import Path
from typing import Any


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


class AppConfig:
    """Loads and provides access to app configuration."""

    def __init__(self, config_file: Path = None):
        self.config_file = config_file or _CONFIG_FILE
        self.config = self._load()

    def _load(self) -> dict:
        """Load config from JSON file, merged with defaults."""
        config = _deep_copy(DEFAULTS)
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    saved = json.load(f)
                _deep_merge(config, saved)
            except Exception:
                pass  # Fall back to defaults on any error
        return config

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """Get a config value. Example: config.get('window', 'max_width')"""
        return self.config.get(section, {}).get(key, fallback)

    def save(self):
        """Save current config to JSON file."""
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)


def _deep_copy(d: dict) -> dict:
    """Deep copy a nested dict (lists are copied too)."""
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _deep_copy(v)
        elif isinstance(v, list):
            result[k] = v[:]
        else:
            result[k] = v
    return result


def _deep_merge(base: dict, override: dict):
    """Merge override values into base, recursively for nested dicts."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


# Global singleton
_instance = None


def get_config() -> AppConfig:
    """Get the global app config instance."""
    global _instance
    if _instance is None:
        _instance = AppConfig()
    return _instance

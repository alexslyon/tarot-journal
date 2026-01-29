"""
Base utilities for JSON configuration files.

Provides deep copy/merge helpers and a base class for JSON configs
with defaults-merging support.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def deep_copy(d: dict) -> dict:
    """
    Deep copy a nested dict (lists are copied too).

    Args:
        d: Dictionary to copy

    Returns:
        A new dictionary with all nested dicts and lists copied
    """
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = deep_copy(v)
        elif isinstance(v, list):
            result[k] = v[:]
        else:
            result[k] = v
    return result


def deep_merge(base: dict, override: dict):
    """
    Merge override values into base, recursively for nested dicts.

    Modifies base in place.

    Args:
        base: The base dictionary to merge into
        override: Values to merge (overrides base)
    """
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            deep_merge(base[k], v)
        else:
            base[k] = v


def shallow_merge(base: dict, override: dict) -> dict:
    """
    Merge override into base at the top level only.

    For each top-level key in override, its entire value replaces
    the corresponding value in base. Useful for theme configs where
    you want to replace entire sections like 'colors' or 'fonts'.

    Args:
        base: The base dictionary (not modified)
        override: Values to merge

    Returns:
        New merged dictionary
    """
    result = deep_copy(base)
    for k, v in override.items():
        if isinstance(v, dict) and k in result and isinstance(result[k], dict):
            # Shallow merge: override values replace base, but missing keys kept from base
            result[k] = {**result[k], **v}
        else:
            result[k] = v
    return result


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """
    Load and parse a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Parsed JSON as dict, or empty dict if file doesn't exist or is invalid

    Raises:
        No exceptions - returns empty dict on error and logs warning
    """
    if not file_path.exists():
        return {}

    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError) as e:
        logger.warning(f"Failed to load JSON from {file_path}: {e}")
        return {}


def save_json_file(file_path: Path, data: dict):
    """
    Save a dictionary to a JSON file.

    Args:
        file_path: Path to save to
        data: Dictionary to save

    Raises:
        IOError, OSError on file write failure
    """
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


class JsonConfig:
    """
    Base class for JSON configuration files with defaults support.

    Subclasses should define:
    - DEFAULTS: class attribute with default configuration
    - Optionally override _get_config_path() to customize file location

    Example:
        class MyConfig(JsonConfig):
            DEFAULTS = {'setting': 'value'}

        config = MyConfig('my_config.json')
        print(config.get('setting'))
    """

    DEFAULTS: Dict[str, Any] = {}

    def __init__(self, config_file: Path, merge_mode: str = 'deep'):
        """
        Initialize config, loading from file and merging with defaults.

        Args:
            config_file: Path to the JSON config file
            merge_mode: 'deep' for recursive merge, 'shallow' for top-level merge
        """
        self.config_file = Path(config_file)
        self.merge_mode = merge_mode
        self.config = self._load()

    def _load(self) -> dict:
        """Load config from file, merged with defaults."""
        config = deep_copy(self.DEFAULTS)
        saved = load_json_file(self.config_file)

        if saved:
            if self.merge_mode == 'deep':
                deep_merge(config, saved)
            else:
                config = shallow_merge(config, saved)

        return config

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """
        Get a config value.

        Args:
            section: Top-level section name
            key: Key within the section
            fallback: Value to return if not found

        Returns:
            The config value, or fallback if not found
        """
        return self.config.get(section, {}).get(key, fallback)

    def set(self, section: str, key: str, value: Any):
        """
        Set a config value.

        Args:
            section: Top-level section name
            key: Key within the section
            value: Value to set
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value

    def save(self):
        """Save current config to file."""
        try:
            save_json_file(self.config_file, self.config)
        except (IOError, OSError) as e:
            logger.error(f"Failed to save config to {self.config_file}: {e}")

    def reload(self):
        """Reload config from file."""
        self.config = self._load()

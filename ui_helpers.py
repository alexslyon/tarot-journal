"""
Shared UI utilities for Tarot Journal wxPython GUI.

Provides theme colors, color conversion, and common constants
used across all UI modules.
"""

import wx
from theme_config import get_theme, PRESET_THEMES
from logger_config import get_logger
from app_config import get_config

logger = get_logger('app')
_cfg = get_config()

# Version
VERSION = "0.4.0"

# Load theme
_theme = get_theme()
COLORS = _theme.get_colors()
_fonts_config = _theme.get_fonts()


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_wx_color(key):
    """Get a wx.Colour from theme"""
    return wx.Colour(*hex_to_rgb(COLORS.get(key, '#000000')))


def refresh_colors():
    """Reload COLORS and _fonts_config after a theme change.

    Updates the dicts in-place so every module that imported them
    sees the new values without needing to re-import.
    """
    COLORS.clear()
    COLORS.update(_theme.get_colors())
    _fonts_config.clear()
    _fonts_config.update(_theme.get_fonts())

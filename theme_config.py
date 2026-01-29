"""
Theme configuration for customizable colors and fonts
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Default theme (Anki-style dark)
DEFAULT_THEME = {
    'colors': {
        'bg_primary': '#1e2024',      # Main background
        'bg_secondary': '#2a2d32',    # Cards, panels
        'bg_tertiary': '#35393f',     # Hover states, borders
        'bg_input': '#3d4148',        # Input fields
        'accent': '#5294e2',          # Primary accent (blue)
        'accent_hover': '#6ba3eb',    # Accent hover
        'accent_dim': '#3d6a99',      # Muted accent
        'text_primary': '#e8e9eb',    # Main text
        'text_secondary': '#9ba0a8',  # Muted text
        'text_dim': '#6b7280',        # Very muted
        'border': '#404552',          # Borders
        'success': '#5cb85c',         # Green
        'warning': '#f0ad4e',         # Orange
        'danger': '#d9534f',          # Red
        'card_slot': '#292c31',       # Empty card slot
    },
    'fonts': {
        'family_display': 'SF Pro Display',
        'family_text': 'SF Pro Text', 
        'family_mono': 'SF Mono',
        'size_title': 22,
        'size_heading': 14,
        'size_body': 12,
        'size_small': 10,
    }
}

# Some preset themes
PRESET_THEMES = {
    'Dark (Default)': DEFAULT_THEME,
    'Light': {
        'colors': {
            'bg_primary': '#f5f5f5',
            'bg_secondary': '#ffffff',
            'bg_tertiary': '#e8e8e8',
            'bg_input': '#ffffff',
            'accent': '#2563eb',
            'accent_hover': '#3b82f6',
            'accent_dim': '#93c5fd',
            'text_primary': '#1f2937',
            'text_secondary': '#6b7280',
            'text_dim': '#9ca3af',
            'border': '#d1d5db',
            'success': '#22c55e',
            'warning': '#f59e0b',
            'danger': '#ef4444',
            'card_slot': '#e5e7eb',
        },
        'fonts': {
            'family_display': 'SF Pro Display',
            'family_text': 'SF Pro Text',
            'family_mono': 'SF Mono',
            'size_title': 22,
            'size_heading': 14,
            'size_body': 12,
            'size_small': 10,
        }
    },
    'Midnight Purple': {
        'colors': {
            'bg_primary': '#1a1625',
            'bg_secondary': '#2d2640',
            'bg_tertiary': '#3d3555',
            'bg_input': '#4a4165',
            'accent': '#9d8cff',
            'accent_hover': '#b8abff',
            'accent_dim': '#6b5b95',
            'text_primary': '#f0e6ff',
            'text_secondary': '#b8a8d4',
            'text_dim': '#8878a8',
            'border': '#5a4a7a',
            'success': '#7dd87d',
            'warning': '#f0c060',
            'danger': '#e06060',
            'card_slot': '#252035',
        },
        'fonts': {
            'family_display': 'SF Pro Display',
            'family_text': 'SF Pro Text',
            'family_mono': 'SF Mono',
            'size_title': 22,
            'size_heading': 14,
            'size_body': 12,
            'size_small': 10,
        }
    },
    'Forest Green': {
        'colors': {
            'bg_primary': '#1a2420',
            'bg_secondary': '#243530',
            'bg_tertiary': '#2e4540',
            'bg_input': '#385550',
            'accent': '#4ade80',
            'accent_hover': '#6ee7a0',
            'accent_dim': '#2d6a4f',
            'text_primary': '#e8f5e9',
            'text_secondary': '#a5d6a7',
            'text_dim': '#6b9b7a',
            'border': '#3d5a50',
            'success': '#4ade80',
            'warning': '#fbbf24',
            'danger': '#f87171',
            'card_slot': '#1e2e28',
        },
        'fonts': {
            'family_display': 'SF Pro Display',
            'family_text': 'SF Pro Text',
            'family_mono': 'SF Mono',
            'size_title': 22,
            'size_heading': 14,
            'size_body': 12,
            'size_small': 10,
        }
    },
}


class ThemeConfig:
    """Manages theme configuration with persistence"""
    
    def __init__(self, config_file: str = None):
        if config_file is None:
            self.config_file = Path(os.path.dirname(os.path.abspath(__file__))) / 'theme_config.json'
        else:
            self.config_file = Path(config_file)
        
        self.theme = self._load_theme()
    
    def _load_theme(self) -> Dict[str, Any]:
        """Load theme from file or return default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    theme = {
                        'colors': {**DEFAULT_THEME['colors'], **saved.get('colors', {})},
                        'fonts': {**DEFAULT_THEME['fonts'], **saved.get('fonts', {})}
                    }
                    return theme
            except (json.JSONDecodeError, IOError, OSError) as e:
                logger.warning(f"Error loading theme: {e}")
        return DEFAULT_THEME.copy()
    
    def save_theme(self):
        """Save current theme to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.theme, f, indent=2)
        except (IOError, OSError) as e:
            logger.error(f"Error saving theme: {e}")
    
    def get_colors(self) -> Dict[str, str]:
        """Get current color scheme"""
        return self.theme['colors']
    
    def get_fonts(self) -> Dict[str, Any]:
        """Get current font settings"""
        return self.theme['fonts']
    
    def set_color(self, key: str, value: str):
        """Set a single color value"""
        if key in self.theme['colors']:
            self.theme['colors'][key] = value
    
    def set_font(self, key: str, value: Any):
        """Set a single font value"""
        if key in self.theme['fonts']:
            self.theme['fonts'][key] = value
    
    def apply_preset(self, preset_name: str):
        """Apply a preset theme"""
        if preset_name in PRESET_THEMES:
            preset = PRESET_THEMES[preset_name]
            self.theme = {
                'colors': preset['colors'].copy(),
                'fonts': preset['fonts'].copy()
            }
    
    def get_preset_names(self) -> list:
        """Get list of available preset themes"""
        return list(PRESET_THEMES.keys())
    
    def export_css(self) -> str:
        """Export theme as CSS variables (for reference)"""
        css = ":root {\n"
        for key, value in self.theme['colors'].items():
            css += f"  --{key.replace('_', '-')}: {value};\n"
        css += f"  --font-display: '{self.theme['fonts']['family_display']}';\n"
        css += f"  --font-text: '{self.theme['fonts']['family_text']}';\n"
        css += f"  --font-mono: '{self.theme['fonts']['family_mono']}';\n"
        css += "}\n"
        return css


# Global instance
_theme_instance = None


def get_theme() -> ThemeConfig:
    """Get the global theme config instance"""
    global _theme_instance
    if _theme_instance is None:
        _theme_instance = ThemeConfig()
    return _theme_instance


def get_colors() -> Dict[str, str]:
    """Convenience function to get current colors"""
    return get_theme().get_colors()


def get_fonts() -> Dict[str, Any]:
    """Convenience function to get current fonts"""
    return get_theme().get_fonts()

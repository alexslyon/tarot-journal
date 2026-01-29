"""
Security utilities for path validation and input sanitization.

This module prevents path traversal attacks by ensuring that file paths
stay within expected directories before serving or reading them.
"""

import os
from pathlib import Path
from typing import Optional, List

# Image file extensions we allow serving
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'}


def is_safe_path(path: str, allowed_directories: Optional[List[str]] = None) -> bool:
    """
    Check if a file path is safe to access.

    A path is considered safe if:
    1. It resolves to a real path (no symlink tricks)
    2. It doesn't contain path traversal patterns
    3. If allowed_directories is provided, the resolved path must be within one of them

    Args:
        path: The file path to validate
        allowed_directories: Optional list of directories the path must be within

    Returns:
        True if the path is safe, False otherwise
    """
    if not path:
        return False

    try:
        # Resolve to absolute path, following symlinks
        real_path = os.path.realpath(path)

        # Check for null bytes (can be used to truncate paths in some systems)
        if '\x00' in path:
            return False

        # If no directory restrictions, just check the file exists
        if allowed_directories is None:
            return os.path.exists(real_path)

        # Check if the resolved path is within any of the allowed directories
        for allowed_dir in allowed_directories:
            allowed_real = os.path.realpath(allowed_dir)
            # Use os.path.commonpath to check containment
            try:
                common = os.path.commonpath([real_path, allowed_real])
                if common == allowed_real:
                    return True
            except ValueError:
                # Paths on different drives (Windows) - not allowed
                continue

        return False

    except (OSError, TypeError, ValueError):
        return False


def is_valid_image_path(path: str, allowed_directories: Optional[List[str]] = None) -> bool:
    """
    Check if a path points to a valid image file.

    Args:
        path: The file path to validate
        allowed_directories: Optional list of directories the path must be within

    Returns:
        True if the path is a valid, accessible image file
    """
    if not path:
        return False

    # Check extension
    ext = os.path.splitext(path)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False

    # Check path safety
    if not is_safe_path(path, allowed_directories):
        return False

    # Verify it's actually a file (not a directory)
    real_path = os.path.realpath(path)
    return os.path.isfile(real_path)


def is_valid_directory(path: str, must_exist: bool = True) -> bool:
    """
    Check if a path is a valid, accessible directory.

    Args:
        path: The directory path to validate
        must_exist: If True, the directory must already exist

    Returns:
        True if the path is a valid directory
    """
    if not path:
        return False

    try:
        # Check for null bytes
        if '\x00' in path:
            return False

        # Resolve to real path
        real_path = os.path.realpath(path)

        if must_exist:
            return os.path.isdir(real_path)

        # If it doesn't need to exist, just check it's a valid path format
        return True

    except (OSError, TypeError, ValueError):
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent directory traversal.

    Removes path separators and other potentially dangerous characters,
    keeping only alphanumeric characters, spaces, underscores, hyphens,
    and periods.

    Args:
        filename: The filename to sanitize

    Returns:
        A sanitized filename safe for use in file paths
    """
    if not filename:
        return ""

    # Get just the basename (remove any path components)
    name = os.path.basename(filename)

    # Keep only safe characters
    safe_chars = []
    for c in name:
        if c.isalnum() or c in ' _-.' :
            safe_chars.append(c)

    result = ''.join(safe_chars).strip()

    # Ensure we don't return an empty string or just dots
    if not result or result.replace('.', '') == '':
        return "unnamed"

    return result

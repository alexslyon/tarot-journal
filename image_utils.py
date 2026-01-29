"""
Image loading and scaling utilities for consistent image handling.

All image loading in this application should go through these functions to ensure:
- EXIF orientation is always handled correctly
- Consistent resampling quality (LANCZOS)
- Proper RGB conversion for display
- Optional rotation for reversed/rotated cards

This module consolidates image loading code that was previously duplicated
across thumbnail_cache.py, card_dialogs.py, mixin_journal.py, and mixin_library.py.
"""

import logging
import os
from typing import Optional, Tuple, Union

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Default background color for transparency replacement (matches dark theme)
DEFAULT_BACKGROUND = (30, 32, 36)


def load_pil_image(image_path: str) -> Optional[Image.Image]:
    """
    Load an image and apply EXIF orientation correction.

    This should be the first step when loading any image, as phone/camera
    images often have rotation stored in EXIF metadata rather than in
    the actual pixel data.

    Args:
        image_path: Path to the image file

    Returns:
        PIL Image with correct orientation, or None if loading fails
    """
    if not image_path or not os.path.exists(image_path):
        return None

    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)
        return img
    except Exception as e:
        logger.warning(f"Error loading image {image_path}: {e}")
        return None


def scale_pil_image(
    img: Image.Image,
    max_size: Tuple[int, int],
    use_thumbnail: bool = False
) -> Image.Image:
    """
    Scale an image to fit within max_size while preserving aspect ratio.

    Args:
        img: PIL Image to scale
        max_size: (max_width, max_height) tuple
        use_thumbnail: If True, use PIL's thumbnail() method which modifies
                      in place and may be slightly faster. If False, use
                      resize() which returns a new image.

    Returns:
        Scaled PIL Image
    """
    max_width, max_height = max_size
    orig_width, orig_height = img.size

    if orig_width <= 0 or orig_height <= 0:
        return img

    if use_thumbnail:
        # thumbnail() modifies in place
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        return img

    # Calculate scale to fit within bounds
    scale = min(max_width / orig_width, max_height / orig_height)
    new_width = int(orig_width * scale)
    new_height = int(orig_height * scale)

    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def convert_to_rgb(
    img: Image.Image,
    background_color: Tuple[int, int, int] = DEFAULT_BACKGROUND
) -> Image.Image:
    """
    Convert an image to RGB mode, handling transparency.

    Images with transparency (RGBA, palette mode) have the transparent
    areas filled with the background color before conversion.

    Args:
        img: PIL Image to convert
        background_color: RGB tuple for transparency fill (default: dark theme bg)

    Returns:
        RGB PIL Image
    """
    if img.mode == 'RGB':
        return img

    if img.mode in ('RGBA', 'P'):
        background = Image.new('RGB', img.size, background_color)
        if img.mode == 'P':
            img = img.convert('RGBA')
        # Paste with alpha mask if available
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[-1])
        else:
            background.paste(img)
        return background

    return img.convert('RGB')


def pil_to_wx_image(pil_img: Image.Image):
    """
    Convert a PIL Image to a wx.Image.

    The PIL image should already be in RGB mode. Call convert_to_rgb()
    first if needed.

    Args:
        pil_img: PIL Image in RGB mode

    Returns:
        wx.Image object
    """
    import wx

    width, height = pil_img.size
    wx_img = wx.Image(width, height)
    wx_img.SetData(pil_img.tobytes())
    return wx_img


def load_and_scale_image(
    image_path: str,
    max_size: Tuple[int, int],
    rotation: int = 0,
    as_wx_image: bool = False,
    as_wx_bitmap: bool = False,
    background_color: Tuple[int, int, int] = DEFAULT_BACKGROUND
) -> Optional[Union[Image.Image, "wx.Image", "wx.Bitmap"]]:
    """
    Load, scale, and optionally convert an image in one step.

    This is the main convenience function that handles the full pipeline:
    1. Load image and apply EXIF orientation
    2. Apply rotation (for reversed cards or rotated spread positions)
    3. Scale to fit within max_size
    4. Convert to RGB (handling transparency)
    5. Optionally convert to wx.Image or wx.Bitmap

    Args:
        image_path: Path to the image file
        max_size: (max_width, max_height) tuple
        rotation: Degrees to rotate (0, 90, 180, 270)
        as_wx_image: If True, return wx.Image instead of PIL Image
        as_wx_bitmap: If True, return wx.Bitmap (implies as_wx_image)
        background_color: RGB tuple for transparency fill

    Returns:
        Scaled image (PIL, wx.Image, or wx.Bitmap), or None if loading fails
    """
    img = load_pil_image(image_path)
    if img is None:
        return None

    try:
        # Apply rotation if needed (for reversed cards or rotated positions)
        if rotation:
            img = img.rotate(rotation, expand=True)

        # Scale to fit
        img = scale_pil_image(img, max_size)

        # Convert to RGB
        img = convert_to_rgb(img, background_color)

        # Convert to wx format if requested
        if as_wx_bitmap or as_wx_image:
            import wx
            wx_img = pil_to_wx_image(img)
            if as_wx_bitmap:
                return wx.Bitmap(wx_img)
            return wx_img

        return img

    except Exception as e:
        logger.warning(f"Error processing image {image_path}: {e}")
        return None


def load_and_scale_for_thumbnail(
    image_path: str,
    size: Tuple[int, int],
    background_color: Tuple[int, int, int] = DEFAULT_BACKGROUND
) -> Optional[Image.Image]:
    """
    Load and scale an image for thumbnail caching.

    Uses PIL's thumbnail() method for efficient scaling.

    Args:
        image_path: Path to the image file
        size: (width, height) for thumbnail
        background_color: RGB tuple for transparency fill

    Returns:
        PIL Image suitable for saving as thumbnail, or None if loading fails
    """
    img = load_pil_image(image_path)
    if img is None:
        return None

    try:
        img = scale_pil_image(img, size, use_thumbnail=True)
        img = convert_to_rgb(img, background_color)
        return img
    except Exception as e:
        logger.warning(f"Error creating thumbnail for {image_path}: {e}")
        return None


def load_for_spread_display(
    image_path: str,
    slot_size: Tuple[int, int],
    is_reversed: bool = False,
    is_position_rotated: bool = False
) -> Optional["wx.Image"]:
    """
    Load an image for spread display with proper rotation handling.

    This handles the special cases for tarot spread layouts:
    - Reversed cards (180 degree rotation)
    - Rotated positions (90 degree rotation, like Celtic Cross challenge position)

    Args:
        image_path: Path to the card image
        slot_size: (width, height) of the spread slot
        is_reversed: If True, rotate 180 degrees for reversed card
        is_position_rotated: If True, rotate 90 degrees (applied first)

    Returns:
        wx.Image ready for display, or None if loading fails
    """
    # Calculate total rotation
    rotation = 0
    if is_position_rotated:
        rotation = 90
    if is_reversed:
        rotation += 180

    # Adjust max size for rotated positions
    w, h = slot_size
    if is_position_rotated:
        # For rotated cards, we need different scaling logic
        # Scale based on width since the card will be horizontal
        max_size = (w - 4, h * 2)  # Allow taller since it will be rotated
    else:
        max_size = (w - 4, h - 4)  # Leave small margin

    return load_and_scale_image(
        image_path,
        max_size,
        rotation=rotation,
        as_wx_image=True
    )

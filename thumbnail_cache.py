"""
Thumbnail caching system for fast image loading
"""

import hashlib
import logging
import os
import threading
from pathlib import Path
from queue import Empty, Queue
from typing import Optional, Tuple

from PIL import Image

from app_config import get_config
from image_utils import load_and_scale_for_thumbnail

logger = logging.getLogger(__name__)

_cfg = get_config()


class ThumbnailCache:
    """Manages thumbnail generation and caching for card images"""

    THUMBNAIL_SIZE = tuple(_cfg.get("images", "thumbnail_size", [300, 450]))
    PREVIEW_SIZE = tuple(_cfg.get("images", "preview_size", [500, 750]))

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            # Default to a .cache folder in the app directory
            cache_dir_name = _cfg.get("paths", "thumbnail_cache_dir", ".thumbnail_cache")
            self.cache_dir = Path(os.path.dirname(os.path.abspath(__file__))) / cache_dir_name
        else:
            self.cache_dir = Path(cache_dir)
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for PhotoImage objects (managed by caller)
        self._memory_cache = {}
        self._cache_lock = threading.Lock()
        
        # Background processing queue
        self._queue = Queue()
        self._worker_thread = None
        self._running = False
    
    def _get_cache_key(self, image_path: str, size: Tuple[int, int]) -> str:
        """Generate a unique cache key for an image at a specific size"""
        # Use path + modification time + size for cache key
        try:
            mtime = os.path.getmtime(image_path)
        except OSError:
            mtime = 0
        
        key_string = f"{image_path}:{mtime}:{size[0]}x{size[1]}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cached thumbnail"""
        return self.cache_dir / f"{cache_key}.png"
    
    def get_thumbnail(self, image_path: str, size: Tuple[int, int] = None) -> Optional[Image.Image]:
        """
        Get a thumbnail for an image, creating it if necessary.
        Returns a PIL Image object.
        """
        if size is None:
            size = self.THUMBNAIL_SIZE
        
        if not image_path or not os.path.exists(image_path):
            return None
        
        cache_key = self._get_cache_key(image_path, size)
        cache_path = self._get_cache_path(cache_key)
        
        # Check if cached thumbnail exists
        if cache_path.exists():
            try:
                return Image.open(cache_path)
            except Exception as e:
                # Corrupted cache file, regenerate
                logger.debug("Corrupted cache file %s, regenerating: %s", cache_path, e)
                cache_path.unlink(missing_ok=True)
        
        # Generate thumbnail using shared utility
        img = load_and_scale_for_thumbnail(image_path, size)
        if img is None:
            return None

        try:
            img.save(cache_path, 'PNG', optimize=True)
            return img
        except Exception as e:
            logger.warning(f"Error saving thumbnail for {image_path}: {e}")
            return None
    
    def get_thumbnail_path(self, image_path: str, size: Tuple[int, int] = None) -> Optional[str]:
        """
        Get the path to a cached thumbnail, creating it if necessary.
        Returns the path to the thumbnail file.
        """
        if size is None:
            size = self.THUMBNAIL_SIZE
        
        if not image_path or not os.path.exists(image_path):
            return None
        
        cache_key = self._get_cache_key(image_path, size)
        cache_path = self._get_cache_path(cache_key)
        
        # Check if cached thumbnail exists and is valid
        if cache_path.exists():
            return str(cache_path)
        
        # Generate thumbnail
        thumb = self.get_thumbnail(image_path, size)
        if thumb:
            return str(cache_path)
        
        return None
    
    def pregenerate_thumbnails(self, image_paths: list, size: Tuple[int, int] = None,
                               callback=None):
        """
        Pre-generate thumbnails for a list of images.
        Optionally calls callback(current, total) for progress updates.
        """
        if size is None:
            size = self.THUMBNAIL_SIZE
        
        total = len(image_paths)
        for i, path in enumerate(image_paths):
            if path and os.path.exists(path):
                self.get_thumbnail(path, size)
            if callback:
                callback(i + 1, total)
    
    def start_background_worker(self):
        """Start a background thread for thumbnail generation"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._running = True
            self._worker_thread = threading.Thread(target=self._background_worker, daemon=True)
            self._worker_thread.start()
    
    def stop_background_worker(self):
        """Stop the background worker thread"""
        self._running = False
        self._queue.put(None)  # Signal to stop
    
    def _background_worker(self):
        """Background worker that processes thumbnail requests"""
        while self._running:
            try:
                item = self._queue.get(timeout=1)
                if item is None:
                    break

                image_path, size, callback = item
                thumb = self.get_thumbnail(image_path, size)
                if callback:
                    callback(image_path, thumb)

            except Empty:
                # Queue timeout - expected, just continue polling
                continue
            except Exception as e:
                logger.debug("Background thumbnail worker error: %s", e)
                continue
    
    def queue_thumbnail(self, image_path: str, size: Tuple[int, int] = None, callback=None):
        """Queue a thumbnail for background generation"""
        if size is None:
            size = self.THUMBNAIL_SIZE
        
        self.start_background_worker()
        self._queue.put((image_path, size, callback))
    
    def clear_cache(self):
        """Clear all cached thumbnails"""
        for file in self.cache_dir.glob('*.png'):
            try:
                file.unlink()
            except OSError as e:
                logger.debug("Failed to delete cache file %s: %s", file, e)
    
    def get_cache_size(self) -> int:
        """Get the total size of the cache in bytes"""
        total = 0
        for file in self.cache_dir.glob('*.png'):
            try:
                total += file.stat().st_size
            except OSError:
                # File may have been deleted between glob and stat
                pass
        return total
    
    def get_cache_count(self) -> int:
        """Get the number of cached thumbnails"""
        return len(list(self.cache_dir.glob('*.png')))


# Global cache instance
_cache_instance = None


def get_cache() -> ThumbnailCache:
    """Get the global thumbnail cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ThumbnailCache()
    return _cache_instance

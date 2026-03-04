"""Simple in-memory cache with TTL for vacation data.

Caches the parsed XLSX data to avoid re-reading the file on every request.
Thread-safe via threading.Lock — safe for Gunicorn multi-worker is handled
at OS process level (each worker has its own cache instance). The lock
protects against race conditions within a single worker under threading.
"""

import logging
import threading
import time
from datetime import date
from pathlib import Path

from screen.ingest.parser import expand_ranges, load_xlsx

logger: logging.Logger = logging.getLogger(__name__)


class CachedData:
    """Thread-safe in-memory cache with timestamp-based TTL.

    Attributes:
        _data: Cached vacation day counts.
        _timestamp: Time when data was last loaded.
        _path: Path that was used to load the data.
        _lock: Reentrant lock to protect concurrent access (S-14).
    """

    def __init__(self) -> None:
        self._data: dict[date, int] | None = None
        self._timestamp: float = 0.0
        self._path: str = ""
        self._lock: threading.Lock = threading.Lock()

    def get_or_refresh(self, path: Path, ttl_minutes: int) -> dict[date, int]:
        """Return cached data or reload from XLSX if stale.

        Uses a double-checked locking pattern: fast path without lock,
        slow path (reload) with lock to prevent concurrent disk reads.

        Args:
            path: Path to the XLSX file.
            ttl_minutes: Cache lifetime in minutes.

        Returns:
            Dictionary mapping dates to vacation counts.
        """
        now: float = time.monotonic()
        path_str: str = str(path)
        ttl_seconds: float = ttl_minutes * 60.0

        # Fast path — check without acquiring the lock first
        if (
            self._data is not None
            and self._path == path_str
            and (now - self._timestamp) < ttl_seconds
        ):
            return self._data

        # Slow path — acquire lock and re-check (double-checked locking)
        with self._lock:
            now = time.monotonic()
            if (
                self._data is not None
                and self._path == path_str
                and (now - self._timestamp) < ttl_seconds
            ):
                return self._data  # Another thread already refreshed

            logger.info("Cache miss or expired, reloading from %s", path)
            try:
                ranges = load_xlsx(path)
                self._data = expand_ranges(ranges)
                self._timestamp = now
                self._path = path_str
            except (FileNotFoundError, ValueError) as e:
                logger.error("Failed to load XLSX: %s", e)
                if self._data is not None:
                    logger.warning("Using stale cached data")
                    return self._data
                return {}

            return self._data

    def invalidate(self) -> None:
        """Force cache invalidation on next access."""
        with self._lock:
            self._timestamp = 0.0


# Module-level singleton
_cache: CachedData = CachedData()


def get_vacation_data(path: Path, ttl_minutes: int) -> dict[date, int]:
    """Get vacation data, using cache if available.

    Args:
        path: Path to the XLSX file.
        ttl_minutes: Cache TTL in minutes.

    Returns:
        Date-to-count mapping.
    """
    return _cache.get_or_refresh(path, ttl_minutes)


def invalidate_cache() -> None:
    """Invalidate the cached data."""
    _cache.invalidate()

import json
import os
from datetime import datetime, timedelta
from filelock import FileLock
from typing import Optional, Any, Dict


class Cache:
    """Unified cache system with TTL support and file locking."""

    def __init__(self, cache_file: str, lock_file: str, ttl_seconds: int = 1800):
        self.cache_file = cache_file
        self.lock_file = lock_file
        self.ttl_seconds = ttl_seconds
        self._lock = FileLock(lock_file)

    def _is_expired(self, timestamp_str: str) -> bool:
        """Check if a cached timestamp has expired."""
        try:
            cached_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            # If TTL is 0, never expire
            if self.ttl_seconds == 0:
                return False
            return datetime.now() - cached_time > timedelta(seconds=self.ttl_seconds)
        except ValueError:
            return True  # If parsing fails, treat as expired

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache if not expired."""
        with self._lock:
            if not os.path.exists(self.cache_file):
                return None

            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return None

            entry = cache_data.get(key)
            if not entry:
                return None

            timestamp = entry.get('timestamp')
            if not timestamp or self._is_expired(timestamp):
                return None

            return entry.get('data')

    def set(self, key: str, value: Any) -> None:
        """Set a value in cache with current timestamp."""
        with self._lock:
            # Load existing cache
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, 'r') as f:
                        cache_data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    cache_data = {}
            else:
                cache_data = {}

            # Update cache
            cache_data[key] = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data': value
            }

            # Save cache
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

    def delete(self, key: str) -> None:
        """Delete a specific key from cache."""
        with self._lock:
            if not os.path.exists(self.cache_file):
                return

            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return

            if key in cache_data:
                del cache_data[key]

            # Save updated cache
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

    def cleanup(self) -> None:
        """Remove expired entries from cache."""
        with self._lock:
            if not os.path.exists(self.cache_file):
                return

            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return

            # Filter out expired entries
            cleaned_cache = {}
            for key, entry in cache_data.items():
                timestamp = entry.get('timestamp')
                if timestamp and not self._is_expired(timestamp):
                    cleaned_cache[key] = entry

            # Save cleaned cache
            with open(self.cache_file, 'w') as f:
                json.dump(cleaned_cache, f, indent=2)


# Global cache instances
youtube_cache = Cache('youtube_api_cache.json', 'youtube_api_cache.lock', 3600)  # 1 hour
state_cache = Cache('channel_states.json', 'channel_states.lock', 0)  # No TTL for states

import time
import threading
from typing import Dict, Any, Optional

from cache import state_cache
from config import config
from youtube_api import youtube_api
from notifications import notification_service


class MonitorService:
    """Background monitoring service for YouTube channels."""

    def __init__(self):
        self.is_running = False
        self.monitor_thread: Optional[threading.Thread] = None

    def start_monitoring(self) -> None:
        """Start the monitoring service in background thread."""
        if self.is_running:
            return

        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("YouTube monitoring started in background")

    def stop_monitoring(self) -> None:
        """Stop the monitoring service."""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        print("YouTube monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_running:
            if not config.youtube_api_key:
                print("Error: YOUTUBE_API_KEY environment variable is not set")
                break

            self._check_channels()
            print(f"Next check in {config.check_interval} seconds...")
            time.sleep(config.check_interval)

    def _check_channels(self) -> None:
        """Check all channels for new videos."""
        channel_states = state_cache.get('channel_states') or {}

        for identifier, current_channel_id in config.channels.items():
            # If current_channel_id is empty, this is a username that needs conversion
            if not current_channel_id:
                # This is a username, convert it first
                actual_channel_id = youtube_api.get_channel_id(identifier)
                if actual_channel_id:
                    # Update the config with the converted channel ID
                    config.update_channel_conversion(identifier, actual_channel_id)
                    print(f"Converted {identifier} to {actual_channel_id}")
                else:
                    print(f"Could not convert {identifier}, skipping...")
                    continue
            else:
                # This is already a channel ID
                actual_channel_id = current_channel_id

            if not actual_channel_id or not actual_channel_id.strip():
                continue

            print(f"\nChecking channel: {actual_channel_id}")
            channel_info = youtube_api.get_channel_info(actual_channel_id)

            if not channel_info or not channel_info.get('latest_video'):
                print("No videos found or error fetching channel data")
                continue

            video = channel_info['latest_video']
            last_video_id = channel_states.get(actual_channel_id)

            if last_video_id != video['id']:
                print(f"New video detected: {video['title']}")
                print(f"Video URL: {video['url']}")

                # Update state
                channel_states[actual_channel_id] = video['id']
                state_cache.set('channel_states', channel_states)

                # Send notification if this isn't the first video we know about
                if last_video_id is not None:
                    notification_service.send_video_notification(channel_info['title'], video)
            else:
                print("No new videos")


# Global monitor service instance
monitor_service = MonitorService()

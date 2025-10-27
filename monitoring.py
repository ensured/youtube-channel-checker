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
        """Check all channels for new videos using batch API calls."""
        channel_states = state_cache.get('channel_states') or {}

        print(f"DEBUG: Loaded channel_states from cache: {channel_states}")

        # Collect all channel IDs that need to be checked
        channel_ids_to_check = []
        channel_id_to_identifier = {}

        for identifier, current_channel_id in config.channels.items():
            # If current_channel_id is empty, this is a username that needs conversion
            if not current_channel_id:
                # This is a username, convert it first
                actual_channel_id = youtube_api.get_channel_id(identifier)
                if actual_channel_id:
                    # Update the config with the converted channel ID
                    config.update_channel_conversion(identifier, actual_channel_id)
                    print(f"Converted {identifier} to {actual_channel_id}")
                    channel_ids_to_check.append(actual_channel_id)
                    channel_id_to_identifier[actual_channel_id] = identifier
                else:
                    print(f"Could not convert {identifier}, skipping...")
                    continue
            else:
                # This is already a channel ID
                actual_channel_id = current_channel_id
                channel_ids_to_check.append(actual_channel_id)
                channel_id_to_identifier[actual_channel_id] = identifier

        if not channel_ids_to_check:
            print("No channels to check")
            return

        print(f"\nChecking {len(channel_ids_to_check)} channels using efficient monitoring API...")

        # Use efficient monitoring API that only fetches latest video (not 10 recent videos)
        channels_info = youtube_api.get_multiple_channels_info_monitoring(channel_ids_to_check)

        if not channels_info:
            print("Failed to fetch any channel data")
            return

        # Process each channel's results
        for channel_id, channel_info in channels_info.items():
            if not channel_info or not channel_info.get('latest_video'):
                print(f"No latest video found for channel: {channel_id}")
                continue

            # Get current latest video and last known video
            current_video = channel_info['latest_video']
            last_video_ids = channel_states.get(channel_id, [])

            # If no last video IDs, this is the first check
            if not last_video_ids:
                print(f"First check for {channel_id}, storing latest video: {current_video['title']}")
                channel_states[channel_id] = [current_video['id']]
                state_cache.set('channel_states', channel_states)
                print(f"DEBUG: Saved channel_states to cache: {channel_states}")
                continue

            # Check if this is a new video
            current_video_id = current_video['id']
            if current_video_id not in last_video_ids:
                print(f"Found new video: {current_video['title']}")

                # Update state with current video (keep up to 20 most recent)
                channel_states[channel_id] = [current_video_id] + last_video_ids[:19]
                state_cache.set('channel_states', channel_states)
                print(f"DEBUG: Updated channel_states to cache: {channel_states}")

                # Send notification for the new video
                notification_result = notification_service.send_video_notification(channel_info['title'], current_video)
                if notification_result:
                    print(f"✅ Notification sent successfully for: {current_video['title']}")
                else:
                    print(f"❌ Failed to send notification for: {current_video['title']}")
            else:
                print(f"No new videos for {channel_id}")


# Global monitor service instance
monitor_service = MonitorService()

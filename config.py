import json
import os
from typing import List, Tuple, Dict
from dotenv import load_dotenv
# Load environment variables
load_dotenv()


class Config:
    """Configuration management with channels loaded from JSON file."""
    APP_PASSWORD = os.getenv('PASSWORD')
    def __init__(self):
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        self.resend_api_key = os.getenv('RESEND_API_KEY')
        self.notification_email = os.getenv('NOTIFICATION_EMAIL')
        self.check_interval = int(os.getenv('CHECK_INTERVAL', 1800))
        self.discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
        self.discord_notification_channel_id = int(os.getenv('DISCORD_NOTIFICATION_CHANNEL_ID')) if os.getenv('DISCORD_NOTIFICATION_CHANNEL_ID') else None
        self.discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.channels_file = 'channels_watching.json'
        self.channels = self._load_channels()


    def _load_channels(self) -> Dict[str, str]:
        """Load channels from channels_watching.json file."""
        try:
            if os.path.exists(self.channels_file):
                with open(self.channels_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Return empty dict if file doesn't exist
                return {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load {self.channels_file}: {e}")
            return {}

    def _save_channels(self) -> bool:
        """Save channels to channels_watching.json file."""
        try:
            with open(self.channels_file, 'w', encoding='utf-8') as f:
                json.dump(self.channels, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error saving channels to {self.channels_file}: {e}")
            return False
    def is_configured(self) -> bool:
        """Check if the configuration is valid."""
        return self.youtube_api_key and self.get_channel_ids() and self.APP_PASSWORD
    def get_channel_ids(self) -> List[str]:
        """Get channel IDs from the dictionary values."""
        channel_ids = []
        for identifier, channel_id in self.channels.items():
            if channel_id:  # If channel_id is not empty
                channel_ids.append(channel_id)
            else:  # If channel_id is empty, use the identifier (it might already be a channel ID)
                channel_ids.append(identifier)
        return channel_ids

    def convert_and_add_channel(self, identifier: str, youtube_api=None) -> tuple[bool, str]:
        """Convert identifier to channel ID using YouTube API and add to config."""
        # First, check if it's already a channel ID
        if identifier.startswith('UC') and len(identifier) == 24:
            # It's already a channel ID, use it directly
            channel_id = identifier
        elif youtube_api is None:
            # If no YouTube API provided, just add as-is
            channel_id = identifier
        else:
            # Use YouTube API to get the actual channel ID
            channel_id = youtube_api.get_channel_id(identifier)
            if not channel_id:
                return False, "Could not find channel. Please check the username or channel ID."

        if identifier in self.channels:
            return False, "Channel already exists."

        # Add to dictionary - if it's a username, we'll update the value when converted
        self.channels[identifier] = channel_id
        self._save_channels()
        return True, channel_id

    def update_channel_conversion(self, identifier: str, channel_id: str) -> None:
        """Update a channel entry when conversion happens."""
        if identifier in self.channels:
            self.channels[identifier] = channel_id
            self._save_channels()

    def remove_channel(self, identifier: str) -> bool:
        """Remove a channel from the dictionary."""
        if identifier not in self.channels:
            return False

        del self.channels[identifier]
        self._save_channels()
        return True

    def get_display_name(self, channel_id: str) -> str:
        """Get the display name for a channel ID."""
        # Look for the identifier that maps to this channel ID
        for identifier, mapped_id in self.channels.items():
            if mapped_id == channel_id:
                return identifier

        # Fallback to channel ID if no mapping found
        return channel_id

    def export_channels_to_json(self, filename: str = 'channels_watching.json') -> bool:
        """Export the channels dictionary to a JSON file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.channels, f, indent=2, ensure_ascii=False)
            print(f"Channels exported to {filename}")
            return True
        except Exception as e:
            print(f"Error exporting channels to JSON: {e}")
            return False

    def import_channels_from_json(self, filename: str = 'channels_watching.json') -> bool:
        """Import channels dictionary from a JSON file."""
        try:
            if not os.path.exists(filename):
                print(f"File {filename} does not exist")
                return False

            with open(filename, 'r', encoding='utf-8') as f:
                imported_channels = json.load(f)

            if isinstance(imported_channels, dict):
                self.channels.update(imported_channels)
                self._save_channels()
                print(f"Channels imported from {filename}")
                return True
            else:
                print(f"Invalid format in {filename}. Expected dictionary.")
                return False
        except Exception as e:
            print(f"Error importing channels from JSON: {e}")
            return False

    def update_username(self, old_identifier: str, new_identifier: str) -> bool:
        """Update the username for a channel."""
        if old_identifier not in self.channels:
            return False

        # Update the key in the dictionary
        self.channels[new_identifier] = self.channels.pop(old_identifier)
        self._save_channels()
        return True
    def reload_channels(self):
        """Reload channels from the JSON file."""
        self.channels = self._load_channels()

config = Config()

from typing import Optional, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz
from datetime import datetime

from cache import youtube_cache
from config import config


class YouTubeAPI:
    """YouTube API service with caching and optimized calls."""

    def __init__(self):
        self.youtube = build('youtube', 'v3', developerKey=config.youtube_api_key) if config.youtube_api_key else None

    def get_channel_id(self, identifier: str) -> Optional[str]:
        """Convert username to channel ID if needed, with caching."""
        if not identifier.startswith('@'):
            return identifier  # Already a channel ID

        # Check cache first
        cached_channel_id = youtube_cache.get(f"username_{identifier}")
        if cached_channel_id:
            return cached_channel_id

        # Fetch from API
        try:
            response = self.youtube.search().list(
                part='snippet',
                q=identifier,
                type='channel',
                maxResults=1
            ).execute()

            if not response.get('items'):
                print(f"No channel found with username: {identifier}")
                return None

            channel_id = response['items'][0]['id']['channelId']

            # Cache the result (but we'll be removing this cache soon)
            youtube_cache.set(f"username_{identifier}", channel_id)
            return channel_id

        except HttpError as e:
            print(f"Error searching for channel: {e}")
            return None

    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive channel information."""
        if not self.youtube:
            return None

        # channel_id should already be a proper channel ID
        try:
            # Get both channel details and latest video in one optimized call
            response = self.youtube.channels().list(
                part='snippet,contentDetails,statistics',
                id=channel_id
            ).execute()

            if not response.get('items'):
                return None

            channel_data = response['items'][0]
            snippet = channel_data['snippet']
            statistics = channel_data['statistics']

            # Get the uploads playlist ID for latest video
            uploads_playlist_id = channel_data['contentDetails']['relatedPlaylists']['uploads']

            # Get latest video
            latest_video = self._get_latest_video(uploads_playlist_id, channel_id)

            return {
                'id': channel_id,
                'title': snippet['title'],
                'description': snippet['description'][:200] + '...' if len(snippet['description']) > 200 else snippet['description'],
                'thumbnail': snippet['thumbnails']['default']['url'],
                'subscriber_count': statistics.get('subscriberCount', '0'),
                'video_count': statistics.get('videoCount', '0'),
                'latest_video': latest_video,
                'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except HttpError as e:
            print(f"Error fetching channel info: {e}")
            return None

    def _get_latest_video(self, uploads_playlist_id: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest video from uploads playlist."""
        try:
            response = self.youtube.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=1
            ).execute()

            if not response.get('items'):
                return None

            video = response['items'][0]['snippet']
            return {
                'id': video['resourceId']['videoId'],
                'title': video['title'],
                'published_at': video['publishedAt'],
                'url': f"https://www.youtube.com/watch?v={video['resourceId']['videoId']}"
            }

        except HttpError as e:
            print(f"Error fetching latest video for channel {channel_id}: {e}")
            return None

    def format_notification_date(self, published_at: str) -> str:
        """Format published date for notifications."""
        try:
            published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            pacific = pytz.timezone('US/Pacific')
            return published_date.astimezone(pacific).strftime('%B %d, %Y at %H:%M %Z')
        except:
            return datetime.now().strftime('%B %d, %Y at %H:%M %Z')


# Global YouTube API instance
youtube_api = YouTubeAPI()

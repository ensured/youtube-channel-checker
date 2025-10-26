from typing import Optional, Dict, Any, List
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
        """Convert username, handle, or validate channel ID, with caching."""
        # If it's already a channel ID (24 characters starting with UC), return as-is
        if len(identifier) == 24 and identifier.startswith('UC'):
            return identifier

        # Check cache first
        cached_channel_id = youtube_cache.get(f"username_{identifier}")
        if cached_channel_id:
            return cached_channel_id

        # Handle different identifier types
        try:
            if identifier.startswith('@'):
                # It's a handle, use forHandle parameter (modern approach)
                response = self.youtube.channels().list(
                    part='id',
                    forHandle=identifier  # @username format
                ).execute()

                if not response.get('items'):
                    print(f"No channel found with handle: {identifier}")
                    return None

                channel_id = response['items'][0]['id']

            elif not identifier.startswith('@') and not identifier.startswith('UC'):
                # It's a legacy username, try search as fallback
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

            else:
                # Unknown format, try search as last resort
                response = self.youtube.search().list(
                    part='snippet',
                    q=identifier,
                    type='channel',
                    maxResults=1
                ).execute()

                if not response.get('items'):
                    print(f"No channel found with query: {identifier}")
                    return None

                channel_id = response['items'][0]['id']['channelId']

            # Cache the result
            youtube_cache.set(f"username_{identifier}", channel_id)
            return channel_id

        except HttpError as e:
            print(f"Error fetching channel ID for {identifier}: {e}")
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

            # Get latest video and recent videos
            latest_video = self._get_latest_video(uploads_playlist_id, channel_id)
            recent_videos = self.get_recent_videos(uploads_playlist_id, channel_id, 10)

            return {
                'id': channel_id,
                'title': snippet['title'],
                'description': snippet['description'][:200] + '...' if len(snippet['description']) > 200 else snippet['description'],
                'thumbnail': snippet['thumbnails']['default']['url'],
                'subscriber_count': statistics.get('subscriberCount', '0'),
                'video_count': statistics.get('videoCount', '0'),
                'latest_video': latest_video,
                'recent_videos': recent_videos,  # Add recent videos
                'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except HttpError as e:
            print(f"Error fetching channel info: {e}")
            return None

    def get_multiple_channels_info(self, channel_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive information for multiple channels in one API call."""
        if not self.youtube:
            return {}

        try:
            # YouTube API allows up to 50 channel IDs in one request
            response = self.youtube.channels().list(
                part='snippet,contentDetails,statistics',
                id=','.join(channel_ids)  # Join IDs with commas
            ).execute()

            channels_info = {}
            if not response.get('items'):
                return {}

            for channel_data in response['items']:
                channel_id = channel_data['id']
                snippet = channel_data['snippet']
                statistics = channel_data['statistics']

                # Get the uploads playlist ID
                uploads_playlist_id = channel_data['contentDetails']['relatedPlaylists']['uploads']

                # Get recent videos for this channel
                recent_videos = self.get_recent_videos(uploads_playlist_id, channel_id, 10)

                channels_info[channel_id] = {
                    'id': channel_id,
                    'title': snippet['title'],
                    'description': snippet['description'][:200] + '...' if len(snippet['description']) > 200 else snippet['description'],
                    'thumbnail': snippet['thumbnails']['default']['url'],
                    'subscriber_count': statistics.get('subscriberCount', '0'),
                    'video_count': statistics.get('videoCount', '0'),
                    'recent_videos': recent_videos,
                    'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            return channels_info

        except HttpError as e:
            print(f"Error fetching multiple channels info: {e}")
            return {}

    def get_multiple_channels_info_light(self, channel_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get basic channel information (just thumbnails, no recent videos) for faster loading."""
        if not self.youtube:
            return {}

        try:
            # Check cache first for each channel
            channels_info = {}
            uncached_ids = []

            for channel_id in channel_ids:
                cached_info = youtube_cache.get(f"channel_info_{channel_id}")
                if cached_info:
                    channels_info[channel_id] = cached_info
                else:
                    uncached_ids.append(channel_id)

            # Only fetch uncached channels from API
            if uncached_ids:
                response = self.youtube.channels().list(
                    part='snippet,statistics',
                    id=','.join(uncached_ids)
                ).execute()

                if response.get('items'):
                    for channel_data in response['items']:
                        channel_id = channel_data['id']
                        snippet = channel_data['snippet']
                        statistics = channel_data['statistics']

                        info = {
                            'id': channel_id,
                            'title': snippet['title'],
                            'description': snippet['description'][:200] + '...' if len(snippet['description']) > 200 else snippet['description'],
                            'thumbnail': snippet['thumbnails']['default']['url'],
                            'subscriber_count': statistics.get('subscriberCount', '0'),
                            'video_count': statistics.get('videoCount', '0'),
                            'recent_videos': [],  # Empty for faster loading
                            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }

                        channels_info[channel_id] = info
                        # Cache for 1 hour
                        youtube_cache.set(f"channel_info_{channel_id}", info)

            return channels_info

        except HttpError as e:
            print(f"Error fetching multiple channels info (light): {e}")
            return {}

    def _get_latest_video(self, uploads_playlist_id: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest video from uploads playlist."""
        try:
            response = self.youtube.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=10  # Get up to 10 recent videos
            ).execute()

            if not response.get('items'):
                return None

            # Return the most recent video for basic functionality
            video = response['items'][0]['snippet']
            return {
                'id': video['resourceId']['videoId'],
                'title': video['title'],
                'description': video.get('description', '')[:150] + '...' if len(video.get('description', '')) > 150 else video.get('description', ''),
                'published_at': video['publishedAt'],
                'url': f"https://www.youtube.com/watch?v={video['resourceId']['videoId']}",
                'thumbnail': video['thumbnails']['medium']['url'] if 'thumbnails' in video else '',
                'channel_title': video.get('channelTitle', ''),
                'channel_id': channel_id
            }

        except HttpError as e:
            print(f"Error fetching latest video for channel {channel_id}: {e}")
            return None

    def get_recent_videos(self, uploads_playlist_id: str, channel_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Get multiple recent videos from uploads playlist."""
        try:
            response = self.youtube.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=min(max_results, 50)  # YouTube API limit is 50
            ).execute()

            if not response.get('items'):
                return []

            videos = []
            for item in response['items']:
                video = item['snippet']
                videos.append({
                    'id': video['resourceId']['videoId'],
                    'title': video['title'],
                    'description': video.get('description', '')[:150] + '...' if len(video.get('description', '')) > 150 else video.get('description', ''),
                    'published_at': video['publishedAt'],
                    'url': f"https://www.youtube.com/watch?v={video['resourceId']['videoId']}",
                    'thumbnail': video['thumbnails']['medium']['url'] if 'thumbnails' in video else '',
                    'channel_title': video.get('channelTitle', ''),
                    'channel_id': channel_id
                })

            return videos

        except HttpError as e:
            print(f"Error fetching recent videos for channel {channel_id}: {e}")
            return []

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

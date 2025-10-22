import resend
from typing import Dict, Any, List
from datetime import datetime

from config import config
from youtube_api import youtube_api


class NotificationService:
    """Handle email notifications for new videos."""

    def __init__(self):
        self.is_configured = bool(config.resend_api_key and config.notification_email)
        if self.is_configured:
            resend.api_key = config.resend_api_key

    def send_video_notification(self, channel_name: str, video: Dict[str, Any]) -> bool:
        """Send notification email for new video."""
        if not self.is_configured:
            print("Notification service not configured (missing API key or email)")
            return False

        try:
            formatted_date = youtube_api.format_notification_date(video['published_at'])
            # Sanitize thumbnail URL and description to handle backslashes
            thumbnail_url = video.get('thumbnail', '').replace('\\', '/')
            description = video.get('description', '').replace('\\', '')

            # Use direct f-string interpolation without concatenation
            thumbnail_html = f"<img src='{thumbnail_url}' style='width: 100%; max-width: 480px; height: auto; border-radius: 8px; margin-bottom: 15px;' alt='Video Thumbnail' onerror='this.style.display=\"none\"'>" if thumbnail_url else ""
            description_html = f"<p style='color: #666; font-size: 14px; line-height: 1.5; margin: 0 0 15px 0;'>{description}</p>" if description else ""

            resend.Emails.send({
                "from": "YouTube Notifier <notifications@resend.dev>",
                "to": [config.notification_email],
                "subject": f"🎬 New Video: {channel_name} - {video['title']}",
                "html": f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #ff0000, #cc0000); padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                        <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 700;">🎬 New Video Alert!</h1>
                        <p style="color: #ffcccc; margin: 5px 0 0 0; font-size: 16px; font-weight: 400;">from {channel_name}</p>
                    </div>

                    <!-- Video Content -->
                    <div style="padding: 25px; background-color: #f8f9fa; border: 1px solid #e9ecef; border-top: none; border-radius: 0 0 10px 10px;">
                        <div style="background-color: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                            <!-- Video Thumbnail -->
                            {thumbnail_html}

                            <!-- Video Title -->
                            <h2 style="color: #1a1a1a; margin: 0 0 15px 0; font-size: 22px; font-weight: 700; line-height: 1.3;">{video['title']}</h2>

                            <!-- Video Description -->
                            {description_html}

                            <!-- Metadata -->
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-top: 15px; border-top: 1px solid #eee;">
                                <span style="color: #666; font-size: 13px;">
                                    📅 {formatted_date}
                                </span>
                                <span style="color: #666; font-size: 13px;">
                                    📺 {channel_name}
                                </span>
                            </div>

                            <!-- Watch Button -->
                            <div style="text-align: center;">
                                <a href="{video['url']}"
                                style="display: inline-block; background: linear-gradient(135deg, #ff0000, #cc0000); color: white;
                                        padding: 15px 30px; text-decoration: none; border-radius: 8px;
                                        font-weight: 700; font-size: 16px; box-shadow: 0 4px 15px rgba(255,0,0,0.3);
                                        transition: all 0.3s ease;">
                                    ▶️ Watch on YouTube
                                </a>
                            </div>
                        </div>
                    </div>

                    <!-- Footer -->
                    <div style="padding: 15px; text-align: center; background-color: #f8f9fa; border-radius: 8px; margin-top: 15px;">
                        <p style="color: #666; font-size: 12px; margin: 0; line-height: 1.4;">
                            You're receiving this email because you subscribed to YouTube channel updates.<br>
                            <a href="#" style="color: #ff0000; text-decoration: none;">Manage your subscriptions</a>
                        </p>
                    </div>
                </div>
                """
            })
            print(f"✅ Notification sent for video: {video['title']}")
            return True

        except Exception as e:
            print(f"❌ Failed to send notification: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'json'):
                error_details = e.response.json()
                print("Error details:", error_details)
            return False

    def send_multiple_videos_notification(self, channel_name: str, videos: List[Dict[str, Any]]) -> bool:
        """Send notification email for multiple new videos."""
        if not self.is_configured:
            print("Notification service not configured (missing API key or email)")
            return False

        if not videos:
            return False

        try:
            # Build HTML for multiple videos
            videos_html = ""
            for i, video in enumerate(videos[:10], 1):  # Show up to 10 most recent
                formatted_date = youtube_api.format_notification_date(video['published_at'])
                thumbnail_url = video.get('thumbnail', '').replace('\\', '/')
                thumbnail_html = f"<img src='{thumbnail_url}' style='width: 120px; height: 68px; object-fit: cover; border-radius: 6px; margin-right: 15px;' alt='Video Thumbnail' onerror='this.style.display=\"none\"'>" if thumbnail_url else ""
                description_html = f"<p style='color: #666; font-size: 13px; line-height: 1.4; margin: 8px 0;'>{video.get('description', '')}</p>" if video.get('description') else ""

                videos_html += f"""
                <div style="background-color: white; border-radius: 12px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-left: 4px solid #ff0000; display: flex; align-items: flex-start;">
                    <!-- Video Thumbnail -->
                    <div style="flex-shrink: 0;">
                        {thumbnail_html}
                    </div>

                    <!-- Video Content -->
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                            <h3 style="color: #1a1a1a; margin: 0; font-size: 18px; font-weight: 700; line-height: 1.3; flex: 1;">{i}. {video['title']}</h3>
                        </div>

                        <!-- Video Description -->
                        {description_html}

                        <!-- Metadata -->
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px; padding-top: 12px; border-top: 1px solid #eee;">
                            <span style="color: #666; font-size: 12px;">
                                📅 {formatted_date}
                            </span>
                            <span style="color: #666; font-size: 12px;">
                                📺 {channel_name}
                            </span>
                        </div>

                        <!-- Watch Button -->
                        <div style="margin-top: 12px;">
                            <a href="{video['url']}"
                               style="display: inline-block; background: linear-gradient(135deg, #ff0000, #cc0000); color: white;
                                      padding: 8px 16px; text-decoration: none; border-radius: 6px;
                                      font-weight: 600; font-size: 13px; box-shadow: 0 2px 8px rgba(255,0,0,0.3);">
                                ▶️ Watch Video
                            </a>
                        </div>
                    </div>
                </div>
                """

            # Add note if there are more than 10 videos
            extra_note = ""
            if len(videos) > 10:
                extra_note = f"<div style='background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 15px; margin-top: 20px; text-align: center;'><p style='color: #856404; font-size: 14px; margin: 0; font-style: italic;'>... and {len(videos) - 10} more recent videos from {channel_name}</p></div>"

            resend.Emails.send({
                "from": "YouTube Notifier <notifications@resend.dev>",
                "to": [config.notification_email],
                "subject": f"🎬 {len(videos)} New Videos: {channel_name}",
                "html": f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #ff0000, #cc0000); padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                        <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 700;">🎬 {len(videos)} New Videos!</h1>
                        <p style="color: #ffcccc; margin: 5px 0 0 0; font-size: 16px; font-weight: 400;">from {channel_name}</p>
                    </div>

                    <!-- Videos List -->
                    <div style="padding: 25px; background-color: #f8f9fa; border: 1px solid #e9ecef; border-top: none; border-radius: 0 0 10px 10px;">

                        {videos_html}

                        {extra_note}

                    </div>

                    <!-- Footer -->
                    <div style="padding: 15px; text-align: center; background-color: #f8f9fa; border-radius: 8px; margin-top: 15px;">
                        <p style="color: #666; font-size: 12px; margin: 0; line-height: 1.4;">
                            You're receiving this email because you subscribed to YouTube channel updates.<br>
                            <a href="#" style="color: #ff0000; text-decoration: none;">Manage your subscriptions</a>
                        </p>
                    </div>
                </div>
                """
            })

            print(f"✅ Notification sent for {len(videos)} videos from {channel_name}")
            return True

        except Exception as e:
            print(f"❌ Failed to send multiple videos notification: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'json'):
                error_details = e.response.json()
                print("Error details:", error_details)
            return False


# Global notification service instance
notification_service = NotificationService()

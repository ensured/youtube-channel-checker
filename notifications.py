import resend
from typing import Dict, Any

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

            resend.Emails.send({
                "from": "YouTube Notifier <notifications@resend.dev>",
                "to": [config.notification_email],
                "subject": f"🎬 New Video: {channel_name} - {video['title']}",
                "html": f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #ff0000;">🎥 New Video from {channel_name}!</h2>
                    <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <h3 style="margin-top: 0;">{video['title']}</h3>
                        <p>📅 Published: {formatted_date}</p>
                        <a href="{video['url']}"
                           style="display: inline-block; background-color: #ff0000; color: white;
                                  padding: 10px 20px; text-decoration: none; border-radius: 5px;
                                  margin-top: 10px; font-weight: bold;">
                            Watch on YouTube
                        </a>
                    </div>
                    <p style="color: #666; font-size: 0.9em;">
                        You're receiving this email because you subscribed to YouTube channel updates.
                    </p>
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


# Global notification service instance
notification_service = NotificationService()

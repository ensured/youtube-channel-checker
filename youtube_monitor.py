import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modular services
from config import config
from monitoring import monitor_service
from notifications import notification_service

# Initialize Flask app
app = Flask(__name__)
app.config["DEBUG"] = True


# ---------- Flask routes ----------
@app.route('/')
def index():
    # Create display-friendly list with usernames/channel IDs
    display_channels = []
    for identifier in config.channels.keys():
        display_channels.append(identifier)

    return render_template('frontend_add_channel.html', channel_ids=display_channels)


@app.route('/add_channel', methods=['POST'])
def add_channel():
    data = request.get_json()
    channel_identifier = data.get('channel_id', '').strip()

    if not channel_identifier:
        return jsonify({'error': 'No channel_id provided'}), 400

    from youtube_api import youtube_api
    success, result = config.convert_and_add_channel(channel_identifier, youtube_api)

    if success:
        return jsonify({'status': 'success', 'channel_id': result})
    else:
        return jsonify({'error': result}), 400


@app.route('/remove_channel', methods=['POST'])
def remove_channel():
    data = request.get_json()
    channel_identifier = data.get('channel_id', '').strip()

    if not channel_identifier:
        return jsonify({'error': 'No channel_id provided'}), 400

    if config.remove_channel(channel_identifier):
        return jsonify({'status': 'success', 'channel_id': channel_identifier})
    else:
        return jsonify({'error': 'Channel ID not found'}), 404


@app.route('/get_channel_info', methods=['POST'])
def get_channel_info_endpoint():
    """Get channel information for multiple channels."""
    data = request.get_json()
    channel_ids = data.get('channel_ids', [])

    if not channel_ids:
        return jsonify({'error': 'No channel_ids provided'}), 400

    from youtube_api import youtube_api

    result = {}
    for channel_id in channel_ids:
        info = youtube_api.get_channel_info(channel_id)
        if info:
            result[channel_id] = info
        else:
            result[channel_id] = {
                'id': channel_id,
                'title': channel_id,
                'thumbnail': 'https://www.gstatic.com/youtube/img/originals/promo/ytr-logo-for-search_96x96.png',
                'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    return jsonify(result)


@app.route('/get_channels', methods=['GET'])
def get_channels():
    # Return both identifiers and their channel IDs from the dictionary
    channels = []
    for identifier, channel_id in config.channels.items():
        display_name = identifier
        channels.append({
            'id': channel_id or identifier,  # Use channel_id if available, otherwise identifier
            'display_name': display_name
        })

    return jsonify({'channels': channels})

@app.route('/test_notification', methods=['GET', 'POST'])
def test_notification():
    """Send a test notification email."""
    if not notification_service.is_configured:
        return jsonify({'error': 'Notification service not configured'}), 400

    # Send a test notification
    test_video = {
        'title': 'YouTube Monitor Test',
        'url': 'https://youtube.com',
        'published_at': datetime.now().isoformat()
    }

    success = notification_service.send_video_notification('Test Channel', test_video)

    if success:
        return jsonify({'status': 'success', 'message': 'Test notification sent'})
    else:
        return jsonify({'error': 'Failed to send test notification'}), 500


@app.route('/test_multiple_notifications', methods=['GET', 'POST'])
def test_multiple_notifications():
    """Send a test notification email for multiple videos."""
    if not notification_service.is_configured:
        return jsonify({'error': 'Notification service not configured'}), 400

    # Send test notifications for multiple videos
    test_videos = [
        {
            'title': 'Test Video 1 - Latest Upload',
            'url': 'https://youtube.com/watch?v=test1',
            'published_at': datetime.now().isoformat()
        },
        {
            'title': 'Test Video 2 - Recent Upload',
            'url': 'https://youtube.com/watch?v=test2',
            'published_at': datetime.now().isoformat()
        },
        {
            'title': 'Test Video 3 - Another Upload',
            'url': 'https://youtube.com/watch?v=test3',
            'published_at': datetime.now().isoformat()
        }
    ]

    success = notification_service.send_multiple_videos_notification('Test Channel', test_videos)

    if success:
        return jsonify({'status': 'success', 'message': f'Test notification sent for {len(test_videos)} videos'})
    else:
        return jsonify({'error': 'Failed to send test notification'}), 500
def reload_channels():
    """Reload channels from channels_watching.json file."""
    old_count = len(config.channels)
    config.channels = config._load_channels()
    new_count = len(config.channels)

    return jsonify({
        'status': 'success',
        'message': f'Reloaded channels from {config.channels_file}',
        'old_count': old_count,
        'new_count': new_count,
        'channels': list(config.channels.keys())
    })


@app.before_request
def start_monitor():
    """Launch monitoring in a background thread when Flask starts."""
    monitor_service.start_monitoring()


# ---------- Entry point ----------
if __name__ == "__main__":
    # Check configuration
    if not config.is_configured():
        print("Warning: Missing configuration. Please set the following environment variables:")
        if not config.youtube_api_key:
            print("- YOUTUBE_API_KEY")
        if not config.get_channel_ids():
            print("- Add channels via the web interface")

    print("Starting YouTube Channel Monitor...")
    print(f"Monitoring {len(config.get_channel_ids())} channels")
    print(f"Check interval: {config.check_interval} seconds")
    print(f"Notifications configured: {'Yes' if notification_service.is_configured else 'No - check RESEND_API_KEY and NOTIFICATION_EMAIL'}")

    app.run(host='0.0.0.0', port=5000, use_reloader=True)
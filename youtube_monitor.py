import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from dotenv import load_dotenv
import json
# Load environment variables
load_dotenv()

# Get password from .env
APP_PASSWORD = os.getenv('PASSWORD')

# Import our modular services
from config import config
from monitoring import monitor_service
from notifications import notification_service

# Initialize Flask app
app = Flask(__name__)
app.config["DEBUG"] = True
app.config['SECRET_KEY'] = os.urandom(24)  # Needed for session management

# Middleware to check if user is authenticated
def login_required(f):
    def wrap(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == APP_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid password')
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Modified existing routes with login_required decorator
@app.route('/')
@login_required
def index():
    display_channels = []
    for identifier in config.channels.keys():
        display_channels.append(identifier)
    return render_template('frontend_add_channel.html', channel_ids=display_channels)

@app.route('/add_channel', methods=['POST'])
@login_required
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
@login_required
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
@login_required
def get_channel_info_endpoint():
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
@login_required
def get_channels():
    channels = []
    for identifier, channel_id in config.channels.items():
        display_name = identifier
        channels.append({
            'id': channel_id or identifier,
            'display_name': display_name
        })
    return jsonify({'channels': channels})

@app.route('/test_notification', methods=['GET', 'POST'])
@login_required
def test_notification():
    if not notification_service.is_configured:
        return jsonify({'error': 'Notification service not configured'}), 400
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
@login_required
def test_multiple_notifications():
    if not notification_service.is_configured:
        return jsonify({'error': 'Notification service not configured'}), 400
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



@app.route('/update_username', methods=['POST'])
@login_required
def update_username():
    data = request.get_json()
    old_username = data.get('old_username')
    new_username = data.get('new_username')
    channel_id = data.get('channel_id')
    if not old_username or not new_username or not channel_id:
        return jsonify({'error': 'Missing old_username, new_username, or channel_id'}), 400
    
    # Update the config channels dictionary by popping old key and setting new key
    if old_username in config.channels:
        config.channels[new_username] = config.channels.pop(old_username)
        if config._save_channels():
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Failed to save channels'}), 500
    else:
        return jsonify({'error': 'Old username not found'}), 404

@app.route('/reload_channels')
@login_required
def reload_channels():
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
    if 'logged_in' not in session and request.endpoint != 'login':
        return redirect(url_for('login'))
    monitor_service.start_monitoring()

if __name__ == "__main__":
    if not config.is_configured():
        print("Warning: Missing configuration. Please set the following environment variables:")
        if not config.youtube_api_key:
            print("- YOUTUBE_API_KEY")
        if not config.get_channel_ids():
            print("- Add channels via the web interface")
        if not APP_PASSWORD:
            print("- PASSWORD (in .env file)")
    print("Starting YouTube Channel Monitor...")
    print(f"Monitoring {len(config.get_channel_ids())} channels")
    print(f"Check interval: {config.check_interval} seconds")
    print(f"Notifications configured: {'Yes' if notification_service.is_configured else 'No - check RESEND_API_KEY and NOTIFICATION_EMAIL'}")
    app.run(host='0.0.0.0', port=5001, use_reloader=True)
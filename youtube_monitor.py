import os
import json
import time
import threading
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import resend
from dotenv import load_dotenv
import pytz
from flask import Flask, request, jsonify, render_template
from filelock import FileLock

# Load environment variables
load_dotenv()

# Configuration
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL')
CHANNEL_IDS = os.getenv('CHANNEL_IDS', '').split(',')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '3600'))  # Default: 1 hour

# File to store the last checked video IDs
STATE_FILE = 'channel_states.json'

ENV_FILE = '.env'
ENV_LOCK = '.env.lock'

YOUTUBE_CACHE_FILE = 'youtube_api_cache.json'
YOUTUBE_CACHE_LOCK = 'youtube_api_cache.lock'
CACHE_TTL_SECONDS = 1800  # 30 minutes

USERNAME_CACHE_FILE = 'youtube_username_cache.json'
USERNAME_CACHE_LOCK = 'youtube_username_cache.lock'
USERNAME_CACHE_TTL_SECONDS = 15 * 24 * 3600  # 15 days

app = Flask(__name__)
app.config["DEBUG"] = True


# ---------- Flask routes ----------
@app.route('/')
def index():
    return render_template('frontend_add_channel.html', channel_ids=get_channel_ids())

@app.route('/add_channel', methods=['POST'])
def add_channel():
    data = request.get_json()
    channel_id = data.get('channel_id', '').strip()
    if not channel_id:
        return jsonify({'error': 'No channel_id provided'}), 400
    lock = FileLock(ENV_LOCK)
    with lock:
        ids = get_channel_ids()
        if channel_id in ids:
            return jsonify({'error': 'Channel ID already exists'}), 400
        ids.append(channel_id)
        set_channel_ids(ids)
    return jsonify({'status': 'success', 'channel_id': channel_id})

@app.route('/remove_channel', methods=['POST'])
def remove_channel():
    data = request.get_json()
    channel_id = data.get('channel_id', '').strip()
    if not channel_id:
        return jsonify({'error': 'No channel_id provided'}), 400
    lock = FileLock(ENV_LOCK)
    with lock:
        ids = get_channel_ids()
        if channel_id not in ids:
            return jsonify({'error': 'Channel ID not found'}), 404
        ids.remove(channel_id)
        set_channel_ids(ids)
    return jsonify({'status': 'success', 'channel_id': channel_id})


# ---------- Utility functions ----------
def get_channel_ids():
    if not os.path.exists(ENV_FILE):
        return []
    with open(ENV_FILE, 'r') as f:
        for line in f:
            if line.startswith('CHANNEL_IDS='):
                ids = line.strip().split('=', 1)[1]
                return [x for x in ids.split(',') if x]
    return []

def set_channel_ids(id_list):
    lines = []
    found = False
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith('CHANNEL_IDS='):
                lines[i] = f"CHANNEL_IDS={','.join(id_list)}\n"
                found = True
                break
    if not found:
        lines.append(f"CHANNEL_IDS={','.join(id_list)}\n")
    with open(ENV_FILE, 'w') as f:
        f.writelines(lines)

@app.route('/get_channels', methods=['GET'])
def get_channels():
    ids = get_channel_ids()
    return jsonify({'channel_ids': ids})

def load_channel_states():
    """Load the last known video IDs for each channel."""
    if not os.path.exists(STATE_FILE):
        return {}
    
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_channel_states(states):
    """Save the current video IDs to the state file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(states, f)

def load_youtube_cache():
    if not os.path.exists(YOUTUBE_CACHE_FILE):
        return {}
    try:
        with open(YOUTUBE_CACHE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_youtube_cache(cache):
    with open(YOUTUBE_CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def load_username_cache():
    if not os.path.exists(USERNAME_CACHE_FILE):
        return {}
    try:
        with open(USERNAME_CACHE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_username_cache(cache):
    with open(USERNAME_CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def get_last_fetch_time(channel_identifier):
    if not os.path.exists(YOUTUBE_CACHE_FILE):
        return None
    try:
        with open(YOUTUBE_CACHE_FILE, 'r') as f:
            cache = json.load(f)
        entry = cache.get(channel_identifier)
        if entry:
            return entry.get('timestamp')
        return None
    except Exception:
        return None

def get_channel_id(youtube, identifier):
    """Convert username to channel ID if needed, with persistent caching."""
    import time
    if not identifier.startswith('@'):
        return identifier  # Already a channel ID
    cache_lock = FileLock(USERNAME_CACHE_LOCK)
    with cache_lock:
        cache = load_username_cache()
        entry = cache.get(identifier)
        if entry:
            ts = entry.get('timestamp', 0)
            if time.time() - ts < USERNAME_CACHE_TTL_SECONDS:
                return entry.get('channel_id')
    try:
        response = youtube.search().list(
            part='snippet',
            q=identifier,
            type='channel',
            maxResults=1
        ).execute()
        if not response.get('items'):
            print(f"No channel found with username: {identifier}")
            return None
        channel_id = response['items'][0]['id']['channelId']
        # Save to cache
        with cache_lock:
            cache = load_username_cache()
            cache[identifier] = {'timestamp': time.time(), 'channel_id': channel_id}
            save_username_cache(cache)
        return channel_id
    except HttpError as e:
        print(f"Error searching for channel: {e}")
        return None

def get_latest_video(channel_identifier):
    """Get the latest video from a YouTube channel, with persistent caching."""
    from time import time as now
    cache_lock = FileLock(YOUTUBE_CACHE_LOCK)
    with cache_lock:
        cache = load_youtube_cache()
        cache_entry = cache.get(channel_identifier)
        if cache_entry:
            ts = cache_entry.get('timestamp', 0)
            if now() - ts < CACHE_TTL_SECONDS:
                return cache_entry.get('video')
    # If not cached or expired, fetch from API
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    channel_id = get_channel_id(youtube, channel_identifier)
    if not channel_id:
        return None
    try:
        response = youtube.channels().list(
            part='snippet,contentDetails',
            id=channel_id
        ).execute()
        if not response.get('items'):
            print(f"No channel found with ID: {channel_id}")
            return None
        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        try:
            playlist_items = youtube.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=1
            ).execute()
        except HttpError as e:
            print(f"Error fetching videos for channel {channel_id}: {e}")
            return None
        if not playlist_items.get('items'):
            return None
        video = playlist_items['items'][0]['snippet']
        video_data = {
            'id': video['resourceId']['videoId'],
            'title': video['title'],
            'channel_title': response['items'][0]['snippet']['title'],
            'published_at': video['publishedAt'],
            'url': f"https://www.youtube.com/watch?v={video['resourceId']['videoId']}"
        }
        # Save to cache
        with cache_lock:
            cache = load_youtube_cache()
            cache[channel_identifier] = {'timestamp': now(), 'video': video_data}
            save_youtube_cache(cache)
        return video_data
    except HttpError as e:
        print(f"Error fetching YouTube data: {e}")
        return None

def send_notification(channel_name, video):
    """Send an email notification about the new video."""
    if not RESEND_API_KEY or not NOTIFICATION_EMAIL:
        print("Missing Resend API key or notification email in environment variables")
        return False
    
    resend.api_key = RESEND_API_KEY
    
    try:
        # Format the published date for better readability
        published_date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
        pacific = pytz.timezone('US/Pacific')
        published_date_pst = published_date.astimezone(pacific)
        formatted_date = published_date_pst.strftime('%B %d, %Y at %H:%M %Z')
        
        resend.Emails.send({
            "from": "YouTube Notifier <notifications@resend.dev>",
            "to": [NOTIFICATION_EMAIL],
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

# ---------- Background monitor ----------
def monitor_channels():
    """Runs in a background thread, checks for new videos."""
    if not YOUTUBE_API_KEY:
        print("Error: YOUTUBE_API_KEY environment variable is not set")
        return
    while True:
        channel_states = load_channel_states()
        for channel_id in get_channel_ids():
            if not channel_id.strip():
                continue
            print(f"\nChecking channel: {channel_id}")
            video = get_latest_video(channel_id)
            if not video:
                print("No videos found or error fetching channel data")
                continue
            channel_key = f"channel_{channel_id}"
            last_video_id = channel_states.get(channel_key)
            if last_video_id != video['id']:
                print(f"New video detected: {video['title']}")
                print(f"Video URL: {video['url']}")
                channel_states[channel_key] = video['id']
                save_channel_states(channel_states)
                if last_video_id is not None:
                    send_notification(video['channel_title'], video)
            else:
                print("No new videos")
        print(f"\nNext check in {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)

@app.before_request
def start_monitor():
    """Launch monitoring in a background thread when Flask starts."""
    t = threading.Thread(target=monitor_channels, daemon=True)
    t.start()


# ---------- Entry ----------
if __name__ == "__main__":
    app.run(port=5000, use_reloader=True)
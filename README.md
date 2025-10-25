# YouTube Channel Monitor

A Flask web application that monitors YouTube channels for new videos and sends email and Discord notifications when new content is published.

## Features

- 🎬 Monitor multiple YouTube channels for new videos
- 📧 Email notifications for new videos (using Resend)
- 💬 Discord notifications via webhooks
- 🤖 Discord bot for channel management
- 💾 Persistent caching with TTL (Time To Live)
- 🕐 Background monitoring with configurable intervals
- 🌐 Web interface for managing channel subscriptions
- 🐳 Docker containerization support

## Quick Start

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd youtube-channel-checker
   ```

2. **Set up environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your credentials:

   ```env
   YOUTUBE_API_KEY=your_youtube_api_key_here
   RESEND_API_KEY=your_resend_api_key_here
   NOTIFICATION_EMAIL=your_email@example.com
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**

   - Main app: `python youtube_monitor.py`
   - Discord bot (in a separate terminal): `python discord_bot.py`

5. **Access the web interface**
   Open your browser to `http://localhost:5000`

## Configuration

| Variable             | Description                               | Required |
| -------------------- | ----------------------------------------- | -------- |
| `YOUTUBE_API_KEY`    | YouTube Data API v3 key                   | Yes      |
| `RESEND_API_KEY`     | Resend API key for notifications          | Yes      |
| `NOTIFICATION_EMAIL` | Email address for notifications           | Yes      |
| `CHECK_INTERVAL`     | Check interval in seconds (default: 3600) | No       |
| `DISCORD_BOT_TOKEN`  | Discord bot token for bot commands        | No       |
| `DISCORD_WEBHOOK_URL`| Discord webhook URL for notifications     | No       |

### Initial Setup

1. **Set up environment variables** in your `.env` file:

   ```env
   YOUTUBE_API_KEY=your_youtube_api_key_here
   RESEND_API_KEY=your_resend_api_key_here
   NOTIFICATION_EMAIL=your_email@example.com
   DISCORD_BOT_TOKEN=your_discord_bot_token_here  # Optional
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...  # Optional
   ```

2. **Add channels** via the web interface at `http://localhost:5000`
   - Use usernames like `@joeybadass` or channel IDs like `UC123456789...`
   - The system will automatically convert and store them internally

### Discord Integration

1. **Set up Discord Bot** (for commands):
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application, then add a bot user
   - Copy the bot token and add to `.env` as `DISCORD_BOT_TOKEN`
   - Invite the bot to your server with permissions: **applications.commands** (for slash commands), **Send Messages**, and **Read Message History**
   - To invite, use the OAuth2 URL generator in the Developer Portal with bot scope and the above permissions

   **Note**: If slash commands don't appear immediately, it can take up to 1 hour for global sync. For faster testing in a specific server, uncomment the guild sync code in `discord_bot.py` and replace `YOUR_GUILD_ID` with your server's ID (enable Developer Mode in Discord, right-click server > Copy ID).

2. **Set up Discord Webhook** (for notifications):
   - In your Discord server, create a webhook in the desired channel
   - Copy the webhook URL and add to `.env` as `DISCORD_WEBHOOK_URL`

3. **Run the Discord Bot** (in a separate terminal):
   ```bash
   python discord_bot.py
   ```

   **Discord Bot Commands:**
   - `/add_channel <username_or_id>` - Add a channel to monitor
   - `/remove_channel <identifier>` - Remove a channel
   - `/list_channels` - List monitored channels
   - `/update_username <old_identifier> <new_identifier>` - Update a channel's username

Channels are now stored internally in `.youtube_config.json` rather than in environment variables. This provides:

- **Persistent storage** across application restarts
- **Clean separation** from sensitive API keys
- **User-friendly display** with username mappings
- **Efficient monitoring** using only channel IDs

The system will automatically migrate existing `CHANNEL_IDS` from your `.env` file on first run.

**Adding Channels:**

- Enter usernames like `@joeybadass` or channel IDs like `UC123456789...`
- The system converts usernames to channel IDs automatically
- Web interface shows the friendly names while using efficient channel IDs internally

**Current Display:**
The web interface now shows "Current Channels" with the user-friendly identifiers (usernames or channel IDs) that you entered.

## API Endpoints

- `GET /` - Web interface for managing channels
- `POST /add_channel` - Add a new channel to monitor
- `POST /remove_channel` - Remove a channel from monitoring
- `GET /get_channels` - Get list of monitored channels
- `POST /get_channel_info` - Get detailed channel information

## Docker Support

Build and run with Docker:

```bash
docker-compose up --build
```

## Architecture

The application is organized into modular components:

- **`config.py`** - Configuration management and environment variable handling
- **`cache.py`** - Unified caching system with TTL support
- **`youtube_api.py`** - YouTube API interactions with optimized calls
- **`notifications.py`** - Email and Discord notification service
- **`monitoring.py`** - Background monitoring service
- **`discord_bot.py`** - Discord bot for channel management and commands
- **`youtube_monitor.py`** - Main Flask application and web routes

## Recent Improvements

- ✅ **Discord Integration**: Added bot commands for channel management and webhook notifications
- ✅ **Modular Architecture**: Code separated into focused modules
- ✅ **Unified Caching**: Single cache system replacing duplicate code
- ✅ **Optimized API Calls**: Reduced YouTube API requests through better caching
- ✅ **Configuration Management**: Proper .env file handling with python-dotenv
- ✅ **Error Handling**: Consistent error patterns across all modules
- ✅ **Dependency Management**: Proper version pinning in requirements.txt
- ✅ **Code Simplification**: Reduced from 400+ lines to ~100 lines in main file

## How It Works

### Internal Configuration Storage

The application now stores channel IDs internally using JSON files instead of relying on environment variables:

- **`.youtube_config.json`** - Stores channel IDs and configuration settings
- **`.channel_mapping.json`** - Maps usernames to channel IDs for display purposes
- **`.env`** - Only contains API keys and email settings (no channel IDs)

This approach provides:

- ✅ **Cleaner separation** of sensitive data vs configuration
- ✅ **Better persistence** across application restarts
- ✅ **User-friendly display** while maintaining efficient internal storage
- ✅ **One-time migration** from old .env-based storage

### Username-to-Channel-ID Optimization

When you add a channel using a username (like `@joeybadass`), the system:

1. **Immediately converts** the username to the actual YouTube channel ID (e.g., `UC123456789...`)
2. **Stores only the channel ID** in the configuration, never the username
3. **Uses the channel ID directly** for all monitoring operations
4. **Maintains a mapping** between usernames and channel IDs for display purposes

This eliminates the need for repeated username-to-channel-ID conversions during monitoring, reducing:

- API calls (no more search requests during monitoring)
- Processing time (no string parsing or caching lookups)
- Complexity (simpler monitoring logic)

**Benefits:**

- ⚡ **Faster monitoring**: No username conversion overhead
- 🔄 **Reduced API usage**: One-time conversion instead of repeated searches
- 💾 **Cleaner storage**: Only channel IDs in configuration
- 🛡️ **More reliable**: No dependency on search API during monitoring
- 🏷️ **User-friendly display**: Shows usernames in the web interface

## Cleanup (Optional)

If you had the old version running, you can safely delete these files:

- `youtube_username_cache.json` - No longer needed (username conversion now happens once)
- `youtube_username_cache.lock` - No longer needed
- Old cache files will be automatically cleaned up by the new system

## Getting YouTube API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the YouTube Data API v3
4. Create credentials (API Key)
5. Copy the API key to your `.env` file

## Getting Resend API Key

1. Sign up at [Resend](https://resend.com/)
2. Create a new API key
3. Add the key to your `.env` file
4. Verify your domain for better deliverability

## Getting Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and add a bot user
3. Copy the bot token from the Bot section
4. Add the token to your `.env` file as `DISCORD_BOT_TOKEN`
5. Invite the bot to your server with permissions for reading messages and sending messages

## Getting Discord Webhook URL

1. In your Discord server, go to the channel where you want notifications
2. Click the gear icon (Edit Channel) > Integrations > Create Webhook
3. Copy the webhook URL and add to your `.env` file as `DISCORD_WEBHOOK_URL`

## Troubleshooting

**No videos found**: Check if the channel ID is correct and the channel has public videos.

**API quota exceeded**: YouTube API has daily quotas. Consider increasing your check interval.

**Discord notifications not working**: Verify your Discord webhook URL is correct and the webhook is active.

**Discord bot not responding**: Check that the bot token is correct and the bot is invited to your server with necessary permissions.

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
from config import config

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Config
channels_file = 'channels_watching.json'

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    # Sync slash commands globally
    try:
        synced = await bot.tree.sync()
        print(f'Slash commands synced! Synced {len(synced)} commands.')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

    # If you want to sync to a specific guild (faster for testing), uncomment and add guild ID
    # guild = bot.get_guild(YOUR_GUILD_ID)
    # if guild:
    #     bot.tree.copy_global_to(guild=guild)
    #     await bot.tree.sync(guild=guild)
    #     print(f'Synced commands to guild: {guild.name}')

@bot.event
async def on_message(message):
    # React with 🔥 to all messages in the notification channel
    if config.discord_notification_channel_id and message.channel.id == int(config.discord_notification_channel_id):
        await message.add_reaction('🔥')
        print(f'Added 🔥 reaction to message in {message.channel.name}')

@bot.tree.command(name='add_channel', description='Add a YouTube channel by username or ID')
async def add_channel(interaction: discord.Interaction, identifier: str):
    # Load current channels
    if os.path.exists(channels_file):
        with open(channels_file, 'r') as f:
            channels = json.load(f)
    else:
        channels = {}

    # Check if already exists
    if identifier in channels:
        await interaction.response.send_message(f'Channel {identifier} already exists.')
        return

    # For simplicity, assume it's a username or ID, add directly
    channels[identifier] = identifier  # Assume it's already an ID or handle conversion
    with open(channels_file, 'w') as f:
        json.dump(channels, f, indent=2)

    await interaction.response.send_message(f'Added channel: {identifier}')

@bot.tree.command(name='remove_channel', description='Remove a YouTube channel by identifier')
async def remove_channel(interaction: discord.Interaction, identifier: str):
    if os.path.exists(channels_file):
        with open(channels_file, 'r') as f:
            channels = json.load(f)
    else:
        channels = {}

    if identifier not in channels:
        await interaction.response.send_message(f'Channel {identifier} not found.')
        return

    del channels[identifier]
    with open(channels_file, 'w') as f:
        json.dump(channels, f, indent=2)

    await interaction.response.send_message(f'Removed channel: {identifier}')

@bot.tree.command(name='list_channels', description='List all monitored channels')
async def list_channels(interaction: discord.Interaction):
    if os.path.exists(channels_file):
        with open(channels_file, 'r') as f:
            channels = json.load(f)
    else:
        channels = {}

    if not channels:
        await interaction.response.send_message('No channels monitored.')
        return

    embed = discord.Embed(
        title='📺 Monitored YouTube Channels',
        description='Here are the channels currently being monitored:',
        color=0xff0000
    )

    for i, (identifier, channel_id) in enumerate(channels.items(), 1):
        embed.add_field(
            name=f'{i}. {identifier}',
            value=f'Channel ID: `{channel_id}`',
            inline=False
        )

    embed.set_footer(text=f'Total: {len(channels)} channels')
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='update_username', description='Update username for a channel')
async def update_username(interaction: discord.Interaction, old_identifier: str, new_identifier: str):
    if os.path.exists(channels_file):
        with open(channels_file, 'r') as f:
            channels = json.load(f)
    else:
        channels = {}

    if old_identifier not in channels:
        await interaction.response.send_message(f'Channel {old_identifier} not found.')
        return

    channels[new_identifier] = channels.pop(old_identifier)
    with open(channels_file, 'w') as f:
        json.dump(channels, f, indent=2)

    await interaction.response.send_message(f'Updated username from {old_identifier} to {new_identifier}')

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("Error: DISCORD_BOT_TOKEN not set.")
    else:
        bot.run(token)

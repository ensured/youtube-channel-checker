#!/bin/sh
python youtube_monitor.py &
python discord_bot.py &
wait

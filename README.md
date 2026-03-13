# 247-bot

A Discord bot that aims to stay online **24/7** and continuously play a lofi stream in a voice channel.

## Features
- Auto-reconnect loop: if the Discord gateway disconnects, the bot will relaunch itself.
- Lofi playback loop via FFmpeg (`-stream_loop -1`) with stream reconnect flags.
- Basic commands:
  - `!join` — joins your current voice channel and starts lofi.
  - `!playlofi [url]` — restarts playback using default or custom URL.
  - `!leave` — disconnects from voice.

## Requirements
- Python 3.10+
- FFmpeg installed and available on `PATH`

## Setup
1. Create a Discord bot in the [Discord Developer Portal](https://discord.com/developers/applications), invite it to your server, and enable the **Message Content Intent** if needed for your command setup.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create your environment file:
   ```bash
   cp .env.example .env
   ```
4. Export env vars (or use your own loader):
   ```bash
   export DISCORD_TOKEN="..."
   export LOFI_URL="https://play.streamafrica.net/lofiradio"
   export LOG_LEVEL="INFO"
   ```
5. Start the bot:
   ```bash
   python bot.py
   ```

## Notes
- This bot's 24/7 behavior means it automatically attempts to restart the Discord connection forever when network/service errors happen.
- For true always-on operation, run it under a process manager/system service (e.g., `systemd`, Docker restart policy, PM2, etc.).

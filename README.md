# 247-bot

A Discord bot intended to stay online **24/7** and continuously stream lofi audio in a voice channel.

## Features
- Infinite reconnect loop with exponential backoff if Discord/network disconnects occur.
- Voice playback auto-restart when a stream drops.
- Commands:
  - `!join` — join your current voice channel and start lofi.
  - `!playlofi [url]` — switch to a default/custom stream URL.
  - `!status` — show whether the bot is connected and playing.
  - `!leave` — disconnect from voice.

## Requirements
- Python 3.10+
- FFmpeg available on `PATH`

## Setup
1. Create a bot in the [Discord Developer Portal](https://discord.com/developers/applications).
2. Enable **Message Content Intent** and **Server Members Intent** (if you expand command features later).
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment:
   ```bash
   cp .env.example .env
   export DISCORD_TOKEN="your_token_here"
   export LOFI_URL="https://play.streamafrica.net/lofiradio"
   export LOG_LEVEL="INFO"
   ```
5. Run:
   ```bash
   python bot.py
   ```

## 24/7 operation note
The bot retries forever in-process, but true 24/7 hosting should still use a process manager (systemd, Docker restart policies, PM2, etc.) so machine reboots and host crashes are recovered automatically.

## Security note
If your bot token is ever shared publicly, **immediately regenerate it** in the Discord Developer Portal and update your environment variables.

import asyncio
import logging
import os
from typing import Optional

import discord
from discord.ext import commands


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LOFI_URL = os.getenv(
    "LOFI_URL",
    "https://play.streamafrica.net/lofiradio",
)

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is required.")


logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("247-bot")

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


def build_audio_source(url: str) -> discord.FFmpegPCMAudio:
    before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -stream_loop -1"
    options = "-vn"
    return discord.FFmpegPCMAudio(url, before_options=before_options, options=options)


async def ensure_playing(voice_client: discord.VoiceClient, stream_url: str) -> None:
    if voice_client.is_playing():
        return

    def after_playback(err: Optional[Exception]) -> None:
        if err:
            logger.error("Playback error: %s", err)

        if voice_client.is_connected():
            fut = asyncio.run_coroutine_threadsafe(ensure_playing(voice_client, stream_url), bot.loop)
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to recover playback: %s", exc)

    logger.info("Starting lofi loop playback in channel %s", voice_client.channel)
    voice_client.play(build_audio_source(stream_url), after=after_playback)


@bot.event
async def on_ready() -> None:
    logger.info("Logged in as %s (%s)", bot.user, bot.user.id if bot.user else "unknown")


@bot.command(name="join")
async def join(ctx: commands.Context) -> None:
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("Join a voice channel first.")
        return

    target_channel = ctx.author.voice.channel
    voice_client = ctx.voice_client

    if voice_client and voice_client.channel != target_channel:
        await voice_client.move_to(target_channel)
        await ctx.send(f"Moved to **{target_channel}**.")
    elif not voice_client:
        voice_client = await target_channel.connect(reconnect=True)
        await ctx.send(f"Connected to **{target_channel}**.")

    await ensure_playing(voice_client, LOFI_URL)


@bot.command(name="playlofi")
async def play_lofi(ctx: commands.Context, stream_url: Optional[str] = None) -> None:
    voice_client = ctx.voice_client
    if not voice_client:
        await ctx.send("Use `!join` first so I know where to stream.")
        return

    chosen_url = stream_url or LOFI_URL
    if voice_client.is_playing():
        voice_client.stop()

    await ensure_playing(voice_client, chosen_url)
    await ctx.send("Lofi loop is now playing 24/7.")


@bot.command(name="leave")
async def leave(ctx: commands.Context) -> None:
    if ctx.voice_client:
        await ctx.voice_client.disconnect(force=True)
        await ctx.send("Disconnected.")
    else:
        await ctx.send("I'm not connected to a voice channel.")


async def run_forever() -> None:
    backoff_seconds = 5

    while True:
        try:
            logger.info("Starting Discord client...")
            await bot.start(DISCORD_TOKEN)
        except (discord.GatewayNotFound, discord.ConnectionClosed, OSError) as exc:
            logger.warning("Connection issue (%s). Restarting in %ss...", exc, backoff_seconds)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected crash: %s", exc)
        finally:
            if not bot.is_closed():
                await bot.close()

        await asyncio.sleep(backoff_seconds)


if __name__ == "__main__":
    asyncio.run(run_forever())

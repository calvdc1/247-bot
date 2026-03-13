import asyncio
import logging
import os
from typing import Optional

import discord
from discord.ext import commands


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEFAULT_LOFI_URL = os.getenv("LOFI_URL", "https://play.streamafrica.net/lofiradio")
RETRY_BASE_SECONDS = int(os.getenv("RETRY_BASE_SECONDS", "5"))
RETRY_MAX_SECONDS = int(os.getenv("RETRY_MAX_SECONDS", "60"))


logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("247-bot")

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def build_audio_source(url: str) -> discord.FFmpegPCMAudio:
    before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    options = "-vn"
    return discord.FFmpegPCMAudio(url, before_options=before_options, options=options)


async def ensure_playing(voice_client: discord.VoiceClient, stream_url: str) -> None:
    if not voice_client.is_connected() or voice_client.is_playing():
        return

    loop = asyncio.get_running_loop()

    def after_playback(err: Optional[Exception]) -> None:
        if err:
            logger.error("Playback error: %s", err)

        if voice_client.is_connected() and not voice_client.is_playing():
            logger.info("Playback ended, restarting stream for %s", voice_client.guild.name)
            loop.call_soon_threadsafe(
                asyncio.create_task,
                ensure_playing(voice_client, stream_url),
            )

    logger.info("Starting lofi stream in channel %s", voice_client.channel)
    voice_client.play(build_audio_source(stream_url), after=after_playback)


@bot.event
async def on_ready() -> None:
    logger.info("Logged in as %s (%s)", bot.user, bot.user.id if bot.user else "unknown")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.CommandNotFound):
        return

    logger.exception("Command error in %s: %s", ctx.command, error)
    await ctx.send(f"Error: `{error}`")


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

    await ensure_playing(voice_client, DEFAULT_LOFI_URL)


@bot.command(name="playlofi")
async def play_lofi(ctx: commands.Context, stream_url: Optional[str] = None) -> None:
    voice_client = ctx.voice_client
    if not voice_client:
        await ctx.send("Use `!join` first so I know where to stream.")
        return

    chosen_url = stream_url or DEFAULT_LOFI_URL
    if voice_client.is_playing():
        voice_client.stop()

    await ensure_playing(voice_client, chosen_url)
    await ctx.send(f"Lofi stream set to: {chosen_url}")


@bot.command(name="leave")
async def leave(ctx: commands.Context) -> None:
    if ctx.voice_client:
        await ctx.voice_client.disconnect(force=True)
        await ctx.send("Disconnected.")
    else:
        await ctx.send("I'm not connected to a voice channel.")


@bot.command(name="status")
async def status(ctx: commands.Context) -> None:
    if not ctx.voice_client or not ctx.voice_client.is_connected():
        await ctx.send("I'm online but not connected to voice.")
        return

    channel = ctx.voice_client.channel
    state = "playing" if ctx.voice_client.is_playing() else "idle"
    await ctx.send(f"Connected to **{channel}** and currently **{state}**.")


async def run_forever(token: str) -> None:
    backoff_seconds = max(1, RETRY_BASE_SECONDS)

    while True:
        try:
            logger.info("Starting Discord client...")
            await bot.start(token)
        except (discord.GatewayNotFound, discord.ConnectionClosed, OSError) as exc:
            logger.warning("Connection issue (%s). Restarting in %ss...", exc, backoff_seconds)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected crash: %s", exc)
        finally:
            if not bot.is_closed():
                await bot.close()

        await asyncio.sleep(backoff_seconds)
        backoff_seconds = min(backoff_seconds * 2, max(backoff_seconds, RETRY_MAX_SECONDS))


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is required.")

    asyncio.run(run_forever(token))

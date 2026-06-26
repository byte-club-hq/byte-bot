import asyncio
import html
import logging
import re
from urllib.parse import unquote

import requests
from discord.ext import tasks
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

TIKTOK_PROFILE_URL = "https://www.tiktok.com/@{username}"


def format_tiktok_message(video_path: str) -> str:
    return f"**Tara** Just Posted a TIKTOK! Go check it out!\nhttps://www.tiktok.com{video_path}"


class _SilentYtDlpLogger:
    def debug(self, message):
        pass

    def warning(self, message):
        pass

    def error(self, message):
        pass


def _normalize_tiktok_text(text: str) -> str:
    return html.unescape(unquote(text)).replace("\\u002F", "/").replace("\\/", "/")


def _extract_tiktok_video_path(text: str, username: str) -> str | None:
    matches = re.findall(
        r"(?:https://(?:www\.)?tiktok\.com)?(/@[A-Za-z0-9._]+/video/\d+)",
        _normalize_tiktok_text(text),
        flags=re.IGNORECASE,
    )
    if not matches:
        return None

    normalized_username = username.casefold()
    for match in matches:
        if match.split("/")[1].lstrip("@").casefold() == normalized_username:
            return match

    # TikTok page markup is unstable; if no exact author match exists, so we use the first public video path found.
    return matches[0]


def _get_latest_tiktok_video_path_with_ytdlp(username: str) -> str:
    target = username if username.startswith("tiktokuser:") else TIKTOK_PROFILE_URL.format(username=username)
    with YoutubeDL({
        "quiet": True,
        "no_warnings": True,
        "logger": _SilentYtDlpLogger(),
        "extract_flat": True,
        "playlistend": 1,
        "skip_download": True,
    }) as ydl:
        # Just ask for the newest public entry.
        data = ydl.extract_info(target, download=False)

    entries = data.get("entries") or []
    if not entries:
        raise ValueError("TikTok extractor did not find any public uploads.")

    entry = entries[0]
    for value in (entry.get("webpage_url"), entry.get("url")):
        if not value:
            continue
        path = _extract_tiktok_video_path(value, username)
        if path:
            return path

    video_id = entry.get("id")
    if video_id and str(video_id).isdigit():
        return f"/@{username}/video/{video_id}"

    raise ValueError("TikTok extractor found an upload but could not read its video ID.")


def get_latest_tiktok_video_path(username: str) -> str:
    username = username.strip().lstrip("@")
    if username.startswith("tiktokuser:"):
        return _get_latest_tiktok_video_path_with_ytdlp(username)

    # Try the public profile first, then fall back to yt-dlp if TikTok serves broken markup.
    response = requests.get(
        TIKTOK_PROFILE_URL.format(username=username),
        headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.tiktok.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
        },
        timeout=10,
    )
    response.raise_for_status()

    video_path = _extract_tiktok_video_path(response.text, username)
    if video_path:
        return video_path

    try:
        return _get_latest_tiktok_video_path_with_ytdlp(username)
    except Exception as extractor_error:
        normalized_html = _normalize_tiktok_text(response.text)
        lower_html = normalized_html.lower()
        if "captcha" in lower_html or "verify" in lower_html:
            raise ValueError(
                "TikTok returned a verification page instead of the public profile. "
                f"Extractor fallback also failed: {extractor_error}"
            ) from extractor_error
        if "login" in lower_html and "video" not in lower_html:
            raise ValueError(
                "TikTok returned a login-style page instead of public video markup. "
                f"Extractor fallback also failed: {extractor_error}. "
                "The account may be private, embedding may be disabled, or anonymous scraping may be blocked. "
                "If you know the numeric TikTok channel ID, set TIKTOK_USERNAME=tiktokuser:<channel_id>."
            ) from extractor_error
        raise ValueError(
            "TikTok profile page did not contain a public video link. "
            f"Extractor fallback also failed: {extractor_error}"
        ) from extractor_error


class TikTokTrackerService:
    def __init__(self, bot, discord_channel_id: int, tiktok_username: str):
        self.bot = bot
        self.discord_channel_id = discord_channel_id
        self.tiktok_username = tiktok_username.lstrip("@")
        self.last_processed_tiktok_id: str | None = None

    @tasks.loop(seconds=900)
    async def tiktok_tracker(self):
        try:
            video_path = await asyncio.to_thread(get_latest_tiktok_video_path, self.tiktok_username)
        except Exception:
            logger.exception("Failed to scrape TikTok profile.")
            return

        if self.last_processed_tiktok_id is None:
            # First poll only seeds state.
            self.last_processed_tiktok_id = video_path
            return

        if video_path == self.last_processed_tiktok_id:
            return

        try:
            channel = self.bot.get_channel(self.discord_channel_id) or await self.bot.fetch_channel(
                self.discord_channel_id
            )
            await channel.send(format_tiktok_message(video_path))
        except Exception:
            logger.exception("Failed to send TikTok tracker message.")
            return

        self.last_processed_tiktok_id = video_path

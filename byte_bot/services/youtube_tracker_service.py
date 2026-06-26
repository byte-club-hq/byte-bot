import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests
from discord.ext import tasks

logger = logging.getLogger(__name__)

CHANNELS_LIST_URL = "https://www.googleapis.com/youtube/v3/channels"
PLAYLIST_ITEMS_LIST_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_API_QUOTA_COST = 1
YOUTUBE_MAX_RESULTS = 50


class YouTubeQuotaExceededError(RuntimeError):
    pass


class YouTubeTemporaryError(RuntimeError):
    pass


@dataclass(frozen=True)
class YouTubeVideo:
    video_id: str
    title: str
    published_at: str


def utc_today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def next_utc_day() -> str:
    return (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()


def format_youtube_message(video: YouTubeVideo) -> str:
    return f"**Tara** just posted a video! Go check it out!\nhttps://www.youtube.com/watch?v={video.video_id}"


class YouTubeDataApiClient:
    def __init__(self, api_key: str, database_service):
        self.api_key = api_key
        self.database_service = database_service

    def _get(self, url: str, params: dict[str, str | int]) -> dict:
        last_error = None
        for attempt in range(3):
            # Track rough quota use locally so we can stop for the day once YouTube says we're out.
            quota_used = self.database_service.increment_youtube_quota(utc_today(), YOUTUBE_API_QUOTA_COST)
            logger.info("Estimated YouTube quota used today: %s", quota_used)

            try:
                response = requests.get(url, params={**params, "key": self.api_key}, timeout=10)
            except requests.RequestException as error:
                last_error = error
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise YouTubeTemporaryError(f"YouTube API network error: {error}") from error

            if response.status_code == 403:
                reason = _youtube_error_reason(response)
                if reason in {"quotaExceeded", "dailyLimitExceeded"}:
                    raise YouTubeQuotaExceededError(reason)

            if response.status_code in {429, 500, 502, 503, 504}:
                last_error = requests.HTTPError(f"{response.status_code} from YouTube API")
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise YouTubeTemporaryError(str(last_error)) from last_error

            response.raise_for_status()
            return response.json()

        raise YouTubeTemporaryError(f"YouTube API failed after retries: {last_error}")

    def get_uploads_playlist_id(self, channel_id: str) -> str:
        data = self._get(
            CHANNELS_LIST_URL,
            {
                "part": "contentDetails",
                "id": channel_id,
            },
        )
        items = data.get("items") or []
        if not items:
            raise ValueError("YouTube channel was not found.")

        playlist_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        if not playlist_id:
            raise ValueError("YouTube channel did not expose an uploads playlist.")

        return playlist_id

    def list_latest_uploads(self, playlist_id: str) -> list[YouTubeVideo]:
        data = self._get(
            PLAYLIST_ITEMS_LIST_URL,
            {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": YOUTUBE_MAX_RESULTS,
            },
        )
        videos = []
        for item in data.get("items") or []:
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})
            video_id = content_details.get("videoId") or snippet.get("resourceId", {}).get("videoId")
            published_at = content_details.get("videoPublishedAt") or snippet.get("publishedAt")
            title = snippet.get("title")
            if video_id and published_at and title:
                videos.append(YouTubeVideo(video_id=video_id, title=title, published_at=published_at))

        return videos


def _youtube_error_reason(response) -> str | None:
    try:
        errors = response.json().get("error", {}).get("errors") or []
    except ValueError:
        return None

    if not errors:
        return None
    return errors[0].get("reason")


class YouTubeTrackerService:
    def __init__(
        self,
        bot,
        discord_channel_id: int,
        youtube_channel_id: str,
        youtube_api_key: str,
        database_service,
        interval_seconds: int,
    ):
        self.bot = bot
        self.discord_channel_id = discord_channel_id
        self.youtube_channel_id = youtube_channel_id
        self.database_service = database_service
        self.api_client = YouTubeDataApiClient(youtube_api_key, database_service)
        # `tasks.loop` needs a default interval, then we swap in the configured one.
        self.youtube_tracker.change_interval(seconds=interval_seconds)

    async def ensure_uploads_playlist_id(self) -> str:
        state = self.database_service.get_youtube_tracker_state()
        if state["uploads_playlist_id"]:
            return state["uploads_playlist_id"]

        # Resolve this once, then reuse it on later polls.
        playlist_id = await asyncio.to_thread(self.api_client.get_uploads_playlist_id, self.youtube_channel_id)
        self.database_service.update_youtube_tracker_state(uploads_playlist_id=playlist_id)
        logger.info("Resolved YouTube uploads playlist ID: %s", playlist_id)
        return playlist_id

    @tasks.loop(seconds=900)
    async def youtube_tracker(self):
        # Keep scheduling separate from polling logic so tests can call poll_once() directly.
        await self.poll_once()

    async def poll_once(self) -> None:
        logger.info("YouTube polling starts.")
        today = utc_today()
        self.database_service.reset_youtube_quota_if_needed(today)
        state = self.database_service.get_youtube_tracker_state()
        if state["quota_paused_until"] and today < state["quota_paused_until"]:
            logger.warning("YouTube polling paused until %s due to quota.", state["quota_paused_until"])
            return

        try:
            playlist_id = await self.ensure_uploads_playlist_id()
            videos = await asyncio.to_thread(self.api_client.list_latest_uploads, playlist_id)
        except YouTubeQuotaExceededError:
            paused_until = next_utc_day()
            self.database_service.update_youtube_tracker_state(
                quota_paused_until=paused_until,
                update_quota_paused_until=True,
            )
            logger.warning("YouTube quota exceeded. Polling paused until %s.", paused_until)
            return
        except YouTubeTemporaryError:
            logger.exception("Temporary YouTube API error after retries.")
            return
        except Exception:
            logger.exception("Failed to poll YouTube Data API.")
            return

        if videos:
            latest = max(videos, key=lambda video: video.published_at)
            logger.info("Latest YouTube video found: %s published at %s", latest.video_id, latest.published_at)
        else:
            logger.info("No YouTube uploads returned by playlistItems.list.")

        processed_ids = self.database_service.get_youtube_processed_video_ids()
        if state["last_video_id"] is None:
            # First poll only seeds state so startup does not replay old uploads.
            bootstrap_videos = sorted(videos, key=lambda video: video.published_at)
            for video in bootstrap_videos:
                self.database_service.mark_youtube_video_processed(video.video_id, video.published_at)

            if bootstrap_videos:
                latest = bootstrap_videos[-1]
                self.database_service.update_youtube_tracker_state(
                    last_video_id=latest.video_id,
                    last_published_at=latest.published_at,
                )
                logger.info(
                    "Seeded YouTube tracker with %s existing upload(s); no startup notifications sent.",
                    len(bootstrap_videos),
                )
            logger.info(
                "Estimated YouTube quota used today: %s",
                self.database_service.get_youtube_tracker_state()["estimated_quota_used"],
            )
            return

        new_videos = [video for video in videos if video.video_id not in processed_ids]
        new_videos.sort(key=lambda video: video.published_at)

        for video in videos:
            if video.video_id in processed_ids:
                logger.info("Skipped duplicate YouTube video: %s", video.video_id)

        # Send oldest first so Discord matches publish order.
        channel = None
        for video in new_videos:
            try:
                if channel is None:
                    channel = self.bot.get_channel(self.discord_channel_id) or await self.bot.fetch_channel(
                        self.discord_channel_id
                    )
                await channel.send(format_youtube_message(video))
                logger.info("Sent YouTube notification for %s", video.video_id)
            except Exception:
                logger.exception("Failed to send YouTube tracker message.")
                return

            self.database_service.mark_youtube_video_processed(video.video_id, video.published_at)
            self.database_service.update_youtube_tracker_state(
                last_video_id=video.video_id,
                last_published_at=video.published_at,
            )

        logger.info(
            "Estimated YouTube quota used today: %s",
            self.database_service.get_youtube_tracker_state()["estimated_quota_used"],
        )

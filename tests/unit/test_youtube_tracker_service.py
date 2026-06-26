import pytest

import byte_bot.services.youtube_tracker_service as youtube
from byte_bot.services.database_service import DatabaseService


class MockResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise youtube.requests.HTTPError(str(self.status_code))


def test_format_youtube_message_omits_title():
    video = youtube.YouTubeVideo(video_id="abc123", title="Latest Video", published_at="2026-06-25T00:00:00Z")

    result = youtube.format_youtube_message(video)

    assert result == "**Tara** just posted a video! Go check it out!\nhttps://www.youtube.com/watch?v=abc123"


def test_get_uploads_playlist_id_uses_channels_list(monkeypatch, database_path):
    database_service = DatabaseService(database_path)
    client = youtube.YouTubeDataApiClient("api-key", database_service)

    def fake_get(url, params, timeout):
        assert url == youtube.CHANNELS_LIST_URL
        assert params["part"] == "contentDetails"
        assert params["id"] == "UC123"
        assert params["key"] == "api-key"
        return MockResponse({
            "items": [
                {
                    "contentDetails": {
                        "relatedPlaylists": {
                            "uploads": "UU123",
                        }
                    }
                }
            ]
        })

    monkeypatch.setattr(youtube.requests, "get", fake_get)

    result = client.get_uploads_playlist_id("UC123")

    assert result == "UU123"
    assert database_service.get_youtube_tracker_state()["estimated_quota_used"] == 1


def test_list_latest_uploads_uses_playlist_items_list(monkeypatch, database_path):
    database_service = DatabaseService(database_path)
    client = youtube.YouTubeDataApiClient("api-key", database_service)

    def fake_get(url, params, timeout):
        assert url == youtube.PLAYLIST_ITEMS_LIST_URL
        assert params["part"] == "snippet,contentDetails"
        assert params["playlistId"] == "UU123"
        return MockResponse({
            "items": [
                {
                    "snippet": {"title": "First"},
                    "contentDetails": {
                        "videoId": "abc123",
                        "videoPublishedAt": "2026-06-25T00:00:00Z",
                    },
                }
            ]
        })

    monkeypatch.setattr(youtube.requests, "get", fake_get)

    result = client.list_latest_uploads("UU123")

    assert result == [youtube.YouTubeVideo(video_id="abc123", title="First", published_at="2026-06-25T00:00:00Z")]


def test_quota_exceeded_raises_specific_error(monkeypatch, database_path):
    database_service = DatabaseService(database_path)
    client = youtube.YouTubeDataApiClient("api-key", database_service)

    def fake_get(url, params, timeout):
        return MockResponse(
            {
                "error": {
                    "errors": [
                        {
                            "reason": "quotaExceeded",
                        }
                    ]
                }
            },
            status_code=403,
        )

    monkeypatch.setattr(youtube.requests, "get", fake_get)

    with pytest.raises(youtube.YouTubeQuotaExceededError):
        client.list_latest_uploads("UU123")


def test_processed_youtube_video_ids_are_persisted(database_path):
    database_service = DatabaseService(database_path)

    database_service.mark_youtube_video_processed("abc123", "2026-06-25T00:00:00Z")

    assert database_service.get_youtube_processed_video_ids() == {"abc123"}


class MockChannel:
    def __init__(self):
        self.messages = []

    async def send(self, message):
        self.messages.append(message)


class MockBot:
    def __init__(self):
        self.channel = MockChannel()

    def get_channel(self, channel_id):
        return self.channel


@pytest.mark.asyncio
async def test_poll_once_bootstraps_existing_videos_without_sending(database_path):
    database_service = DatabaseService(database_path)
    database_service.update_youtube_tracker_state(uploads_playlist_id="UU123")
    bot = MockBot()
    service = youtube.YouTubeTrackerService(bot, 123, "UC123", "api-key", database_service, 900)
    service.api_client.list_latest_uploads = lambda playlist_id: [
        youtube.YouTubeVideo(video_id="newer", title="Newer", published_at="2026-06-25T03:00:00Z"),
        youtube.YouTubeVideo(video_id="old", title="Old", published_at="2026-06-25T00:00:00Z"),
    ]

    await service.poll_once()

    state = database_service.get_youtube_tracker_state()
    assert bot.channel.messages == []
    assert state["last_video_id"] == "newer"
    assert database_service.get_youtube_processed_video_ids() == {"old", "newer"}


@pytest.mark.asyncio
async def test_poll_once_sends_new_videos_in_chronological_order_and_skips_duplicates(database_path):
    database_service = DatabaseService(database_path)
    database_service.update_youtube_tracker_state(
        uploads_playlist_id="UU123",
        last_video_id="old",
        last_published_at="2026-06-25T00:00:00Z",
    )
    database_service.mark_youtube_video_processed("old", "2026-06-25T00:00:00Z")
    bot = MockBot()
    service = youtube.YouTubeTrackerService(bot, 123, "UC123", "api-key", database_service, 900)
    service.api_client.list_latest_uploads = lambda playlist_id: [
        youtube.YouTubeVideo(video_id="newer", title="Newer", published_at="2026-06-25T03:00:00Z"),
        youtube.YouTubeVideo(video_id="old", title="Old", published_at="2026-06-25T00:00:00Z"),
        youtube.YouTubeVideo(video_id="newer-duplicate", title="Newer Duplicate", published_at="2026-06-25T02:00:00Z"),
    ]

    await service.poll_once()

    assert bot.channel.messages == [
        "**Tara** just posted a video! Go check it out!\nhttps://www.youtube.com/watch?v=newer-duplicate",
        "**Tara** just posted a video! Go check it out!\nhttps://www.youtube.com/watch?v=newer",
    ]
    assert database_service.get_youtube_processed_video_ids() == {"old", "newer-duplicate", "newer"}

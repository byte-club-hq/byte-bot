import byte_bot.services.tiktok_tracker_service as tiktok
import pytest


class MockResponse:
    text = '<a href="/@byteclub/video/7412345678901234567">latest</a>'

    def raise_for_status(self):
        pass


def test_get_latest_tiktok_video_path_returns_public_video_path(monkeypatch):
    def fake_get(url, headers, timeout):
        return MockResponse()

    monkeypatch.setattr(tiktok.requests, "get", fake_get)

    result = tiktok.get_latest_tiktok_video_path("byteclub")

    assert result == "/@byteclub/video/7412345678901234567"


def test_format_tiktok_message_uses_canonical_www_url():
    result = tiktok.format_tiktok_message("/@byteclub/video/7412345678901234567")

    assert (
        result
        == "**Tara** Just Posted a TIKTOK! Go check it out!\nhttps://www.tiktok.com/@byteclub/video/7412345678901234567"
    )


def test_get_latest_tiktok_video_path_handles_escaped_links(monkeypatch):
    class EscapedResponse:
        text = '"https:\\/\\/www.tiktok.com\\/@ByteClub\\/video\\/7412345678901234567"'

        def raise_for_status(self):
            pass

    def fake_get(url, headers, timeout):
        return EscapedResponse()

    monkeypatch.setattr(tiktok.requests, "get", fake_get)

    result = tiktok.get_latest_tiktok_video_path("byteclub")

    assert result == "/@ByteClub/video/7412345678901234567"


def test_get_latest_tiktok_video_path_falls_back_to_ytdlp(monkeypatch):
    class EmptyProfileResponse:
        text = "<html></html>"

        def raise_for_status(self):
            pass

    class MockYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, url, download):
            return {"entries": [{"id": "7412345678901234567"}]}

    def fake_get(url, headers, timeout):
        return EmptyProfileResponse()

    monkeypatch.setattr(tiktok.requests, "get", fake_get)
    monkeypatch.setattr(tiktok, "YoutubeDL", MockYoutubeDL)

    result = tiktok.get_latest_tiktok_video_path("byteclub")

    assert result == "/@byteclub/video/7412345678901234567"


def test_get_latest_tiktok_video_path_supports_tiktokuser_target(monkeypatch):
    class MockYoutubeDL:
        def __init__(self, options):
            self.options = options

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            pass

        def extract_info(self, url, download):
            assert url == "tiktokuser:123456789"
            return {"entries": [{"webpage_url": "https://www.tiktok.com/@byteclub/video/7412345678901234567"}]}

    monkeypatch.setattr(tiktok, "YoutubeDL", MockYoutubeDL)

    result = tiktok.get_latest_tiktok_video_path("tiktokuser:123456789")

    assert result == "/@byteclub/video/7412345678901234567"


def test_get_latest_tiktok_video_path_reports_extractor_failure(monkeypatch):
    class LoginResponse:
        text = "<html>login</html>"

        def raise_for_status(self):
            pass

    def fake_get(url, headers, timeout):
        return LoginResponse()

    monkeypatch.setattr(tiktok.requests, "get", fake_get)
    monkeypatch.setattr(
        tiktok,
        "_get_latest_tiktok_video_path_with_ytdlp",
        lambda username: (_ for _ in ()).throw(ValueError("embedding disabled")),
    )

    with pytest.raises(ValueError, match="embedding disabled"):
        tiktok.get_latest_tiktok_video_path("byteclub")

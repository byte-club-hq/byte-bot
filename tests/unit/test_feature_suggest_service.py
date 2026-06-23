import pytest

from discord.ext import commands

from byte_bot.services.feature_suggest_service import create_feature_suggestion
from byte_bot.cogs.feature_suggest import ImageURL


def test_create_feature_suggestion_returns_dataclass_for_valid_input():
    result = create_feature_suggestion("Dark Mode", "Add a dark theme for users.")

    assert result.title == "Dark Mode"
    assert result.summary == "Add a dark theme for users."


def test_create_feature_suggestion_allows_max_title_length():
    result = create_feature_suggestion("A" * 256, "Short summary")

    assert result.title == "A" * 256


def test_create_feature_suggestion_raises_for_title_too_long():
    with pytest.raises(ValueError, match="The title cannot exceed 256 characters."):
        create_feature_suggestion("A" * 257, "Short summary")


def test_create_feature_suggestion_allows_max_summary_length():
    result = create_feature_suggestion("Dark Mode", "B" * 1024)

    assert result.summary == "B" * 1024


def test_create_feature_suggestion_raises_for_summary_too_long():
    with pytest.raises(ValueError, match="The summary cannot exceed 1024 characters."):
        create_feature_suggestion("Dark Mode", "B" * 1025)


async def test_imageurl_converter_raises_for_non_https():
    converter = ImageURL()
    with pytest.raises(commands.BadArgument):
        await converter.convert(None, "not-a-url")


async def test_imageurl_converter_returns_url_for_https():
    converter = ImageURL()
    result = await converter.convert(None, "https://thread.com/image.png")

    assert result == "https://thread.com/image.png"


def test_create_feature_suggestion_defaults_image_to_none():
    result = create_feature_suggestion("Dark Mode", "Add a dark theme.")

    assert result.image is None


def test_create_feature_suggestion_stores_valid_image_url():
    result = create_feature_suggestion("Dark Mode", "Add a dark theme.", "https://thread.com/image.png")

    assert result.image == "https://thread.com/image.png"


def test_create_feature_suggestion_raises_for_non_https_image():
    with pytest.raises(ValueError, match="Image URL must be a direct"):
        create_feature_suggestion("Dark Mode", "Short summary", "http://thread.com/image.png")
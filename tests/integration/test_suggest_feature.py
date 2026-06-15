import pytest
from unittest.mock import AsyncMock, MagicMock

import discord
from discord.ext import commands
import discord.ext.test as dpytest

from byte_bot.services.feature_suggest_service import FeatureSuggestion


def _make_forum_channel():
    mock_thread = MagicMock(spec=discord.Thread)
    mock_thread.name = "Test Feature"

    mock_thread_with_message = MagicMock()
    mock_thread_with_message.thread = mock_thread

    mock_channel = MagicMock(spec=discord.ForumChannel)
    mock_channel.create_thread = AsyncMock(return_value=mock_thread_with_message)
    return mock_channel


def _block_dms(monkeypatch):
    async def _raise_forbidden(*args, **kwargs):
        raise discord.Forbidden(MagicMock(), "Cannot send messages to this user")

    monkeypatch.setattr(discord.Member, "send", _raise_forbidden)


def _patch_feature_service(monkeypatch, bot, replacement):
    command = bot.get_command("suggestfeature")
    monkeypatch.setitem(command.callback.__globals__, "create_feature_suggestion", replacement)


@pytest.mark.asyncio
async def test_suggestfeature_created_thread(bot, monkeypatch):
    _block_dms(monkeypatch)
    mock_channel = _make_forum_channel()
    monkeypatch.setattr(bot, "get_channel", lambda _: mock_channel)
    _patch_feature_service(
        monkeypatch,
        bot,
        lambda title, summary: FeatureSuggestion(title=title, summary=summary),
    )

    await dpytest.message('+suggestfeature "Dark Mode" Add a dark theme for users.')

    embed = mock_channel.create_thread.call_args[1]["embed"]
    field_map = {f.name: f.value for f in embed.fields}
    assert mock_channel.create_thread.call_args[1]["name"] == "Dark Mode"
    assert field_map.get("Title") == "Dark Mode"
    assert field_map.get("Summary") == "Add a dark theme for users."


@pytest.mark.asyncio
async def test_suggestfeature_sends_confirmation(bot, monkeypatch):
    _block_dms(monkeypatch)
    monkeypatch.setattr(bot, "get_channel", lambda _: _make_forum_channel())
    _patch_feature_service(
        monkeypatch,
        bot,
        lambda title, summary: FeatureSuggestion(title=title, summary=summary),
    )

    await dpytest.message('+suggestfeature "Dark Mode" Add a dark theme for users.')

    assert dpytest.verify().message().contains().content("submitted")


@pytest.mark.asyncio
async def test_suggestfeature_single_word_title(bot, monkeypatch):
    _block_dms(monkeypatch)
    mock_channel = _make_forum_channel()
    monkeypatch.setattr(bot, "get_channel", lambda _: mock_channel)
    _patch_feature_service(
        monkeypatch,
        bot,
        lambda title, summary: FeatureSuggestion(title=title, summary=summary),
    )

    await dpytest.message("+suggestfeature Notifications Add push notifications.")

    assert mock_channel.create_thread.call_args[1]["name"] == "Notifications"


@pytest.mark.asyncio
async def test_suggestfeature_service_error_is_reported(bot, monkeypatch):
    _block_dms(monkeypatch)
    mock_channel = _make_forum_channel()
    monkeypatch.setattr(bot, "get_channel", lambda _: mock_channel)

    def raise_value_error(title, summary):
        raise ValueError("The title cannot exceed 256 characters.")

    _patch_feature_service(monkeypatch, bot, raise_value_error)

    await dpytest.message('+suggestfeature "Dark Mode" Add a dark theme for users.')

    mock_channel.create_thread.assert_not_called()
    assert dpytest.verify().message().contains().content("256")


@pytest.mark.asyncio
async def test_suggestfeature_no_args(bot, monkeypatch):
    _block_dms(monkeypatch)

    with pytest.raises(commands.MissingRequiredArgument):
        await dpytest.message("+suggestfeature")

    assert dpytest.verify().message().contains().content("+suggestfeature")


@pytest.mark.asyncio
async def test_suggestfeature_missing_summary(bot, monkeypatch):
    _block_dms(monkeypatch)

    with pytest.raises(commands.MissingRequiredArgument):
        await dpytest.message('+suggestfeature "Dark Mode"')

    assert dpytest.verify().message().contains().content("/suggestfeature")


@pytest.mark.asyncio
async def test_suggestfeature_channel_not_found(bot, monkeypatch):
    _block_dms(monkeypatch)
    monkeypatch.setattr(bot, "get_channel", lambda _: None)
    _patch_feature_service(
        monkeypatch,
        bot,
        lambda title, summary: FeatureSuggestion(title=title, summary=summary),
    )

    await dpytest.message('+suggestfeature "Dark Mode" Some summary.')

    assert dpytest.verify().message().contains().content("Could not find the forum channel")


@pytest.mark.asyncio
async def test_suggestfeature_wrong_channel_type(bot, monkeypatch):
    _block_dms(monkeypatch)
    monkeypatch.setattr(bot, "get_channel", lambda _: MagicMock(spec=discord.TextChannel))
    _patch_feature_service(
        monkeypatch,
        bot,
        lambda title, summary: FeatureSuggestion(title=title, summary=summary),
    )

    await dpytest.message('+suggestfeature "Dark Mode" Some summary.')

    assert dpytest.verify().message().contains().content("misconfigured")


@pytest.mark.asyncio
async def test_suggestfeature_wrong_channel_type_no_thread_created(bot, monkeypatch):
    _block_dms(monkeypatch)
    mock_text_channel = MagicMock(spec=discord.TextChannel)
    mock_text_channel.create_thread = AsyncMock()
    monkeypatch.setattr(bot, "get_channel", lambda _: mock_text_channel)
    _patch_feature_service(
        monkeypatch,
        bot,
        lambda title, summary: FeatureSuggestion(title=title, summary=summary),
    )

    await dpytest.message('+suggestfeature "Dark Mode" Some summary.')

    mock_text_channel.create_thread.assert_not_called()


@pytest.mark.asyncio
async def test_suggestfeature_discord_exception(bot, monkeypatch):
    _block_dms(monkeypatch)
    mock_channel = MagicMock(spec=discord.ForumChannel)
    mock_channel.create_thread = AsyncMock(side_effect=discord.DiscordException("API error"))
    monkeypatch.setattr(bot, "get_channel", lambda _: mock_channel)
    _patch_feature_service(
        monkeypatch,
        bot,
        lambda title, summary: FeatureSuggestion(title=title, summary=summary),
    )

    await dpytest.message('+suggestfeature "Dark Mode" Some summary.')

    assert dpytest.verify().message().contains().content("Failed to submit your feature suggestion")

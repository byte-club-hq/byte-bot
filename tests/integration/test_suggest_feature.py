import pytest
from unittest.mock import AsyncMock, MagicMock

import discord
from discord.ext import commands
import discord.ext.test as dpytest

def _make_forum_channel():
    """Return a ForumChannel mock with a working create_thread"""
    mock_thread = MagicMock(spec=discord.Thread)
    mock_thread.name = "Test Feature"

    mock_thread_with_message = MagicMock()
    mock_thread_with_message.thread = mock_thread

    mock_channel = MagicMock(spec=discord.ForumChannel)
    mock_channel.create_thread = AsyncMock(return_value=mock_thread_with_message)
    return mock_channel

def _block_dms(monkeypatch):
    """
    Force Member.send() to raise Forbidden so _reply() falls back to ctx.send().
    dpytest does not queue DMs, so this is required to capture text command replies.
    """
    async def _raise_forbidden(*args, **kwargs):
        raise discord.Forbidden(MagicMock(), "Cannot send messages to this user")

    monkeypatch.setattr(discord.Member, "send", _raise_forbidden)

@pytest.mark.asyncio
async def test_suggestfeature_created_thread(bot, monkeypatch):
    _block_dms(monkeypatch)
    mock_channel = _make_forum_channel()
    monkeypatch.setattr(bot, "get_channel", lambda _: mock_channel)

    await dpytest.message('+suggestfeature "Dark Mode" Add a dark theme for users.')
    
    embed = mock_channel.create_thread.call_args[1]["embed"]
    field_map = {f.name: f.value for f in embed.fields}
    assert field_map.get("Title") == "Dark Mode"
    assert field_map.get("Summary") == "Add a dark theme for users."

@pytest.mark.asyncio
async def test_suggestfeature_sends_confirmation(bot, monkeypatch):
    _block_dms(monkeypatch)
    monkeypatch.setattr(bot, "get_channel", lambda _: _make_forum_channel())

    await dpytest.message('+suggestfeature "Dark Mode" Add a dark theme for users.')

    assert dpytest.verify().message().contains().content("✅")

@pytest.mark.asyncio
async def test_suggestfeature_single_word_title(bot, monkeypatch):
    _block_dms(monkeypatch)
    mock_channel = _make_forum_channel()
    monkeypatch.setattr(bot, "get_channel", lambda _: mock_channel)

    await dpytest.message("+suggestfeature Notifications Add push notifications.")

    assert mock_channel.create_thread.call_args[1]["name"] == "Notifications"

@pytest.mark.asyncio
async def test_suggestfeature_title_too_long(bot, monkeypatch):
    _block_dms(monkeypatch)
    mock_channel = _make_forum_channel()
    monkeypatch.setattr(bot, "get_channel", lambda _: mock_channel)

    await dpytest.message(f'+suggestfeature "{"A" * 257}" Some summary.')

    mock_channel.create_thread.assert_not_called()
    assert dpytest.verify().message().contains().content("256")

@pytest.mark.asyncio
async def test_suggestfeature_summary_too_long(bot, monkeypatch):
    _block_dms(monkeypatch)
    mock_channel = _make_forum_channel()
    monkeypatch.setattr(bot, "get_channel", lambda _: mock_channel)

    await dpytest.message(f'+suggestfeature "Title" {"B" * 1025}')

    mock_channel.create_thread.assert_not_called()
    assert dpytest.verify().message().contains().content("1024")

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

    await dpytest.message('+suggestfeature "Dark Mode" Some summary.')

    assert dpytest.verify().message().contains().content("❌")

@pytest.mark.asyncio
async def test_suggestfeature_wrong_channel_type(bot, monkeypatch):
    _block_dms(monkeypatch)
    monkeypatch.setattr(bot, "get_channel", lambda _: MagicMock(spec=discord.TextChannel))

    await dpytest.message('+suggestfeature "Dark Mode" Some summary.')

    assert dpytest.verify().message().contains().content("misconfigured")

@pytest.mark.asyncio
async def test_suggestfeature_wrong_channel_type_no_thread_created(bot, monkeypatch):
    _block_dms(monkeypatch)
    mock_text_channel = MagicMock(spec=discord.TextChannel)
    mock_text_channel.create_thread = AsyncMock()
    monkeypatch.setattr(bot, "get_channel", lambda _: mock_text_channel)

    await dpytest.message('+suggestfeature "Dark Mode" Some summary.')

    mock_text_channel.create_thread.assert_not_called()

@pytest.mark.asyncio
async def test_suggestfeature_discord_exception(bot, monkeypatch):
    _block_dms(monkeypatch)
    mock_channel = MagicMock(spec=discord.ForumChannel)
    mock_channel.create_thread = AsyncMock(side_effect=discord.DiscordException("API error"))
    monkeypatch.setattr(bot, "get_channel", lambda _: mock_channel)

    await dpytest.message('+suggestfeature "Dark Mode" Some summary.')

    assert dpytest.verify().message().contains().content("❌")
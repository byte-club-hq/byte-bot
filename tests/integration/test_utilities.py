import pytest
import discord.ext.test as dpytest


async def _about_embed():
    await dpytest.message("+about")
    msg = dpytest.get_message()

    assert len(msg.embeds) == 1
    return msg.embeds[0]


@pytest.mark.asyncio
async def test_about_embed_title(bot):
    embed = await _about_embed()
    assert "About" in embed.title


@pytest.mark.asyncio
async def test_about_embed_description(bot):
    embed = await _about_embed()
    assert "Byte Club" in embed.description


@pytest.mark.asyncio
async def test_about_embed_has_status_field(bot):
    embed = await _about_embed()
    field_names = [field.name for field in embed.fields]
    assert "Status" in field_names


@pytest.mark.asyncio
async def test_about_embed_has_metrics_fields(bot):
    embed = await _about_embed()
    field_names = [field.name for field in embed.fields]

    assert any("Ping" in name for name in field_names)
    assert any("Health" in name for name in field_names)
    assert any("Uptime" in name for name in field_names)
    assert any("Users" in name for name in field_names)


@pytest.mark.asyncio
async def test_about_embed_has_github_link(bot):
    embed = await _about_embed()
    assert any("GitHub Repository" in field.value for field in embed.fields)

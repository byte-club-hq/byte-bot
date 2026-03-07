import pytest
import discord.ext.test as dpytest

@pytest.mark.asyncio
async def test_utilities(bot):
    await dpytest.message("+about")
    msg = dpytest.get_message()

    assert len(msg.embeds) == 1
    embed = msg.embeds[0]

    assert "About" in embed.title
    assert "Byte Club" in embed.description

    field_names = [field.name for field in embed.fields]
    assert "Status" in field_names
    assert any("Ping" in name for name in field_names)
    assert any("Health" in name for name in field_names)
    assert any("Uptime" in name for name in field_names)
    assert any("Users" in name for name in field_names)
    assert any("GitHub Repository" in field.value for field in embed.fields)

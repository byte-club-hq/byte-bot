from pathlib import Path
from types import SimpleNamespace

import discord.ext.test as dpytest
import pytest_asyncio

from byte_bot.byte_bot import ByteBot

async def _load_all_cogs(bot: ByteBot) -> None:
    cogs_path = Path(__file__).resolve().parents[1] / "byte_bot" / "cogs"
    for file in sorted(cogs_path.rglob("*.py")):
        if file.name == "__init__.py":
            continue
        module = ".".join(file.relative_to(cogs_path).with_suffix("").parts)
        await bot.load_extension(f"byte_bot.cogs.{module}")

# creates/manages the event loop for async tests/fixtures
@pytest_asyncio.fixture
async def bot():
    test_config = SimpleNamespace(FEATURE_FORUM_CHANNEL_ID=1234567890)
    bot = ByteBot(config=test_config)
    dpytest.configure(bot)
    
    # initialize discord.py async internals
    # bot.loop is usable after this
    await bot._async_setup_hook()
    
    # In tests we skip bot.start()/login, 
    # so extensions are not auto-loaded
    # load cogs explicitly.
    await _load_all_cogs(bot)
    try:
        yield bot
    finally:
        await dpytest.empty_queue()

from datetime import datetime, timezone
import logging
from pathlib import Path

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# Intents determine what events the bot will receive from Discord.
# See https://discordpy.readthedocs.io/en/latest/api.html?highlight=intents#discord.Intents
INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True


class ByteBot(commands.Bot):
    """
    The main bot class that inherits from commands.Bot. This is where we will set up our bot's configuration,
    load cogs, etc.
    """

    def __init__(self, config):
        super().__init__(
            intents=INTENTS,
            # Legacy way to run commands against the bot. (Doesn't include slash commands)
            command_prefix="+",
            # The "activity" to be shown in the Discord rich presence of the bot.
            activity=discord.Activity(typ=discord.ActivityType.competing, name="in leetcode challenges"),
            # Ensure bot doesn't accidentally ping everyone
            allowed_mentions=discord.AllowedMentions(everyone=False),
        )

        self.config = config
        self.feature_forum_channel_id = self.config.FEATURE_FORUM_CHANNEL_ID
        # Recording start time for uptime tracking
        self.start_time = datetime.now(timezone.utc)

    async def setup_hook(self) -> None:
        """Called when the bot is ready to load cogs and interact with the API."""
        
        # Path to the /cogs directory (relative to this file)
        cogs_path = Path(__file__).parent / "cogs"
        
        # Recursively find all Python files inside /cogs
        for file in sorted(cogs_path.rglob("*.py")):
            
            if file.name == "__init__.py" : 
                continue

            # Convert file path to a module path:
            # Example:
            # subfolder/ping.py -> subfolder.ping
            relative = file.relative_to(cogs_path).with_suffix("")
            module = ".".join(relative.parts)
            
            # Load the extension dynamically
            # Final example:
            # byte_bot.cogs.subfolder.ping
            await self.load_extension(f"byte_bot.cogs.{module}")

        # Syncs the application commands (slash commands) with Discord.
        synced = await self.tree.sync()
        log.info(f"Added main cog commands... Synced {len(synced)} commands")

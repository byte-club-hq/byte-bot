import logging

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

    def __init__(self):
        super().__init__(
            intents=INTENTS,
            # Legacy way to run commands against the bot. (Doesn't include slash commands)
            command_prefix="+",
            # The "activity" to be shown in the Discord rich presence of the bot.
            activity=discord.Activity(typ=discord.ActivityType.competing, name="in leetcode challenges"),
            # Ensure bot doesn't accidentally ping everyone
            allowed_mentions=discord.AllowedMentions(everyone=False),
        )

    async def setup_hook(self) -> None:
        """Called when the bot is ready to load cogs and interact with the API."""

        # TODO: Load cogs from the "cogs" directory. This allows us to modularize our commands and event listeners.
        # for cog in SOME_LIST_OF_COGS:
        #     await self.load_extension(cog)

        synced = await self.tree.sync()  # Syncs the application commands (slash commands) with Discord.
        log.info(f"Added main cog commands... Synced {len(synced)} commands")

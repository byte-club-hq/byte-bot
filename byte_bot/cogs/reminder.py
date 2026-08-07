import logging

import discord
from discord import app_commands
from discord.ext import commands

from byte_bot.byte_bot import ByteBot

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEFAULT_REMINDERS = [10] # in minutes

class ReminderCog(commands.Cog):

    reminder = app_commands.Group(
        name="reminder",
        description="Manage reminder events.",
    )
    def __init__(self, bot: ByteBot):
        """
        Initialize the Reminder cog.

        Args:
            bot (ByteBot): The bot instance. Must have the attribute `feature_forum_channel_id` set.
        """
        self.bot = bot
        logger.debug("remindercog init")

    @reminder.command(
            name="list_channels",
            description="List reminder channels"
    )
    @app_commands.guild_only()
    async def list_channels(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        
        if guild is None:
            return

        logger.debug("Fetching reminder channels...")
        db_service = self.bot.database_service

        channels = db_service.get_reminder_channels()

        if len(channels) == 0:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="No reminder channels are set",
                    description="You can add a reminder channel using /reminder add "
                ))
            return

        embed = discord.Embed(
            title="Reminder are set in the following channels",
            color=discord.Color.dark_blue(),
        )
        for channel in channels:
            embed.add_field(
                 name=channel.name,
                 value=(
                    f"id: {channel.id}\n\n"
                 ),
            )

        await interaction.followup.send(embed=embed)


async def setup(bot: ByteBot):
    await bot.add_cog(ReminderCog(bot))

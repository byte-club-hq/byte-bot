import logging

import discord
from discord import app_commands
from discord.ext import commands

from byte_bot.byte_bot import ByteBot

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class EventsCog(commands.Cog):

    events = app_commands.Group(
        name="events",
        description="Manage events reminders",
    )
    def __init__(self, bot: ByteBot):
        """
        Initialize the Events cog.

        Args:
            bot (ByteBot): The bot instance. Must have the attribute `feature_forum_channel_id` set.
        """
        self.bot = bot
    @events.command(
            name="list",
            description="List upcoming events"
    )
    @app_commands.guild_only()
    async def list_events(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild

        if guild is None:
            return

        logger.debug("Fetching scheduled evets ...")
        upcoming_events = await guild.fetch_scheduled_events(
            with_counts=False
        )
        valid_events = [
            event 
            for event in upcoming_events
            if event.status
            not in (
                discord.EventStatus.completed,
                discord.EventStatus.cancelled,
            )
        ]
        if not valid_events:
            await interaction.followup.send(
                "There are no upcoming events",
                ephemeral=True,
            )
            return

        valid_events.sort(key=lambda x: x.start_time)
        
        embed = discord.Embed(
            title="📅 Upcoming Events",
            color=discord.Color.dark_blue(),
        )

        for event in valid_events:
            timestamp = int(event.start_time.timestamp())
            embed.add_field(
                 name=event.name,
                 value=(
                    f"⏱️ <t:{timestamp}:F>\n"
                    f"🔗 {event.url}\n\n"
                 ),
                 inline=False,
            )

        await interaction.followup.send(embed=embed)


async def setup(bot: ByteBot):
    await bot.add_cog(EventsCog(bot))

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from byte_bot.byte_bot import ByteBot

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEFAULT_REMINDERS = [10, 24*60] # in minutes

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
        self.db_service = bot.database_service


    async def cog_load(self):
        self.check_reminders_db.start()

    def cog_unload(self):
        self.check_reminders_db.cancel()

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

        channels = self.db_service.get_reminder_channels()

        if len(channels) == 0:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="No reminder channels are set",
                    description="You can add a reminder channel using /reminder add_channel "
                ))
            return

        embed = discord.Embed(
            title="Reminder are set in the following channels",
            color=discord.Color.dark_blue(),
        )
        logger.debug(len(channels))

        for channel in channels:
            logger.debug(channel.name)
            embed.add_field(
                 name=channel.name,
                 value=(
                    f"id: {channel.id}\n\n"
                 ),
            )

        await interaction.followup.send(embed=embed)


    @reminder.command(
        name="set_channel",
        description="Include a new channel for event reminders"
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer()
        guild = interaction.guild

        if guild is None:
            return

        reminder_channel = self.db_service.set_channel_reminder(channel.id, channel.name)

        await interaction.followup.send(
            f"Event reminders will be sent to {reminder_channel.name}, {reminder_channel.id}.",
            ephemeral=True,
        )


    @reminder.command(
            name="remove_channel",
            description="Remove channel for event reminders"
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def remove_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer()
        guild = interaction.guild

        if guild is None:
            return

        db_service = self.bot.database_service

        reminder_channel = db_service.set_channel_reminder(channel.id, channel.name)

        await interaction.followup.send(
            f"Removed {reminder_channel.name}, {reminder_channel.id} from event reminders",
            ephemeral=True,
        )

    @reminder.command(
                name="list_reminders",
                description="List event reminders"
        )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def get_reminders(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        
        if guild is None:
            return

        logger.debug("Fetching reminders ...")

        reminders = self.db_service.get_reminders()

        if len(reminders) == 0:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="No reminders are set",
                    description="You can add a reminder using"
                ))
            return

        embed = discord.Embed(
            title="Reminder are set in the following channels",
            color=discord.Color.dark_blue(),
        )
        logger.debug(len(reminders))

        for reminder in reminders:
            embed.add_field(
                    name="reminder",
                    value=(
                    f"id: {reminder.id}\n"
                    f"event_id: {reminder.event_id}\n"
                    f"event_name: {reminder.event_name}\n"
                    f"reminder_minutes: {reminder.reminder_minutes}\n"
                    f"event_start: {reminder.event_start}\n"
                    ),
                    inline=False,
            )

        await interaction.followup.send(embed=embed)
    

    @tasks.loop(minutes=30)
    async def check_reminders_db(self):
        await self.process_reminders()

    async def process_reminders(self):
        # get reminder channels
        #channels = self.db_service.get_reminder_channels()
        await self.bot.wait_until_ready()
        logger.debug("process reminders")
        reminders = self.db_service.get_reminders()
        events_w_reminder = set(reminder.event_id for reminder in reminders)
        guild = self.bot.get_channel(self.bot.feature_forum_channel_id).guild
        logger.debug(guild)
        upcoming_events = await guild.fetch_scheduled_events(
                    with_counts=False
                )
        logger.debug(events_w_reminder)
        
        events = [
            event
            for event in upcoming_events
            if event.status
            not in (
                discord.EventStatus.completed,
                discord.EventStatus.cancelled,
            )
        ]
        # check if there are reminders for the event
        for event in events:
            if event.id not in events_w_reminder:
                logger.debug(f"creating for {event.id}, {event.name}")
                # create and event reminder
                for timer_reminder in DEFAULT_REMINDERS:
                    self.db_service.create_reminder(
                        event.id,
                        event.name,
                        timer_reminder,
                        event.start_time,
                    )

    @tasks.loop(seconds=60)
    async def check_reminders(self):
        await self.send_reminders()

    async def send_reminders(self):
        pass

async def setup(bot: ByteBot):
    await bot.add_cog(ReminderCog(bot))

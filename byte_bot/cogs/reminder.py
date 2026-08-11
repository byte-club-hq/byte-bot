import logging
import time
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
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders_db.cancel()
        self.check_reminders.cancel()

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
                    f"event_name: {reminder.text}\n"
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
        await self.bot.wait_until_ready()
        # get reminder channels
        channels = self.db_service.get_reminder_channels()
        channels_ids = [channel.id for channel in channels]
        logger.debug("process reminders")
        reminders = self.db_service.get_reminders()
        events_w_reminder = {reminder.event_id: reminder.event_start for reminder in reminders}
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
            logger.debug(event)
            if event.id in events_w_reminder:
                # Check if the time_start is the same
                # if not update the reminders
                if event.start_time.timestamp != events_w_reminder[event.id]:
                    self.db_service.update_reminder(event.id, event.start_time.timestamp)
                continue

            logger.debug(f"creating for {event.id}, {event.name}")
            # create and event reminder
            for timer_reminder in DEFAULT_REMINDERS:
                for channel_id in channels_ids:
                    self.db_service.create_reminder(
                        event.id,
                        event.name,
                        event.url,
                        event.description,
                        channel_id,
                        timer_reminder,
                        event.start_time
                    )

    async def send_reminder(self, reminder):
        guild = self.bot.get_channel(self.bot.feature_forum_channel_id).guild
        channel = guild.get_channel(reminder.channel_id)
        time_text = (
                f"{reminder.reminder_minutes//60} hours" 
                if reminder.reminder_minutes > 60 
                else f"{reminder.reminder_minutes} minutes")

        embed = discord.Embed(
            title="🔔 Event reminder",
            description=(
                f"**{reminder.event_name}**\n\n"
                f"⏰ Starts in **{time_text}**.\n\n"
                f"<t:{reminder.event_start}:F>\n\n"
                f"{reminder.text}"
            ),
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="Event",
            value=reminder.event_url
        )

        await channel.sent(embed=embed)

    @tasks.loop(seconds=60)
    async def check_reminders(self):
        await self.bot.wait_until_ready()
        reminders = self.db_service.get_reminders()
        now = int(time.time()) # get the now timestamp in abs seconds
        
        for reminder in reminders:
            reminder_seconds = reminder.reminder_minutes*60
            if 0 < reminder.event_start - now <= reminder_seconds:
                self.send_reminder(reminder)

                self.db_service.mark_reminder_sent(
                    reminder.id, now
                )

async def setup(bot: ByteBot):
    await bot.add_cog(ReminderCog(bot))

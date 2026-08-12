import logging
import time
import discord
from discord import app_commands
from discord.ext import commands, tasks

from byte_bot.byte_bot import ByteBot
from byte_bot.services.reminder_service import ReminderService

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEFAULT_REMINDERS = (
        10, # ten minutes 
        24*60 # 24 hours
    )

def format_reminder_time(minutes: int) -> str:
    """Format the time to show in discord message."""
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    hours = minutes // 60
    remaining_minutes = minutes%60

    if remaining_minutes == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"

    return (
        f"{hours} hour{'s' if hours != 1 else ''} "
        f"{remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"
    )
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
        logger.debug("Reminder cog init")
        self.db_service = ReminderService(bot.database_service)

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

        logger.debug("Fetching reminder channels...")

        channels = self.db_service.get_reminder_channels()

        if not channels:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="No reminder channels are set",
                    description="You can add a reminder channel using /reminder add_channel "
                ))
            return

        embed = discord.Embed(
            title="Reminders are set in the following channels",
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
            f"Event reminders will be sent to {reminder_channel.name}, channel id: {reminder_channel.id}.",
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

        is_removed = self.db_service.remove_reminder_channel(channel.id)

        if is_removed:
            await interaction.followup.send(
                f"Removed {channel.name}, {channel.id} from event reminders",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"The channel is not set up to receive reminders.",
            ephemeral=True,
        )  

    @reminder.command(
                name="list_reminders",
                description="List event reminders"
        )
    @app_commands.guild_only()
    async def list_reminders(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        
        if guild is None:
            return

        reminders = self.db_service.get_pending_reminders()

        if len(reminders) == 0:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="No reminders are set",
                    description="You can add a reminder using"
                ))
            return

        embed = discord.Embed(
            title="Reminders are the following",
            color=discord.Color.dark_blue(),
        )

        for reminder in reminders:
            embed.add_field(
                    name="reminder",
                    value=(
                    f"id: {reminder.id}\n"
                    f"event_id: {reminder.event_id}\n"
                    f"event_name: {reminder.event_name}\n"
                    f"event_name: {reminder.text}\n"
                    f"url: {reminder.url}\n"
                    f"reminder_minutes: {reminder.reminder_minutes}\n"
                    f"event_start: {reminder.event_start}\n"
                    ),
                    inline=False,
            )

        await interaction.followup.send(embed=embed)
    
    @tasks.loop(minutes=30)
    async def process_reminders(self):
        # get reminder channels
        channels = self.db_service.get_reminder_channels()
        channels_ids = [channel.id for channel in channels]
        logger.debug("Process reminders")
        reminders = self.db_service.get_pending_reminders()
        events_w_reminder = {reminder.event_id: reminder.event_start for reminder in reminders}
        guild = self.bot.get_channel(self.bot.feature_forum_channel_id).guild
        upcoming_events = await guild.fetch_scheduled_events(
                    with_counts=False
                )
        
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
            if event.id in events_w_reminder:
                # Check if the time_start is the same
                # if not update the reminders
                start_time = int(event.start_time.timestamp()) 
                if start_time!= events_w_reminder[event.id]:
                    self.db_service.update_reminder_start_time(event.id, start_time)
                continue

            logger.debug(f"Creating reminder for {event.id}, {event.name}")
            # create and event reminder
            for timer_reminder in DEFAULT_REMINDERS:
                for channel_id in channels_ids:
                    self.db_service.create_reminder(
                        event.id,
                        event.name,
                        event.url,
                        event.description or "",
                        channel_id,
                        timer_reminder,
                        event.start_time
                    )

    @process_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    async def send_reminder(self, reminder):
        try:
            channel = await self.bot.fetch_channel(reminder.channel_id)
        except Exception as e:
            logger.error(
                f"Reminder channel {reminder.channel_id} was not found"
            )
            return False
        
        time_text = format_reminder_time(reminder.reminder_minutes) 

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
            value=reminder.url
        )

        await channel.send(embed=embed)

        return True

    @tasks.loop(seconds=60)
    async def check_reminders(self):
        reminders = self.db_service.get_pending_reminders()
        now = int(time.time()) # get the now timestamp in abs seconds
        
        for reminder in reminders:
            reminder_seconds = reminder.reminder_minutes*60
            if 0 < reminder.event_start - now <= reminder_seconds:
                try: 
                    sent = await self.send_reminder(reminder)
                    if sent:
                        self.db_service.mark_reminder_sent(
                        reminder.id,
                        now,
                    )
                except Exception as e:
                    logger.exception(
                        f"Failed to send reminder {reminder.id}"
                    )

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    @reminder.command(
                name="change_text",
                description="Change the reminders text content given the event id."
        )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def change_reminder_text(self, interaction: discord.Interaction, event_id: int, text: str):
        await interaction.response.defer(ephemeral=True)

        if not text.strip():
            await interaction.followup.send("Reminder text cannot be empty.")
            return
        
        logger.debug(f"Updating reminder text for event {event_id}")

        reminders = self.db_service.update_reminder_text(event_id, text)
        
        if not reminders:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="No reminders found",
                    description=f"No unsent reminders were found for event {event_id}."
                ))
            return

        embed = discord.Embed(
            title="Reminders text updated",
            description=(
                f"Updated {len(reminders)} reminder(s) "
                f"for event `{event_id}`."
            ),
            color=discord.Color.dark_blue(),
        )

        for reminder in reminders:
            embed.add_field(
                name=f"Reminder #{reminder.id}",
                value=(
                    f"**Event:** {reminder.event_name}\n"
                    f"**Channel ID:** {reminder.channel_id}\n"
                    f"**Reminder:** {reminder.reminder_minutes} minutes\n"
                    f"**Text:** {reminder.text}"
                ),
                inline=False,
            )

        await interaction.followup.send(embed=embed)

async def setup(bot: ByteBot):
    await bot.add_cog(ReminderCog(bot))

import logging
import time
import discord
from discord import app_commands
from discord.ext import commands, tasks

from byte_bot.byte_bot import ByteBot
from byte_bot.services.reminder_service import ReminderService, Reminder

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEFAULT_REMINDERS = (
        10, # 10 minutes 
        24*60 # 24 hours
    )

REMINDER_THRESHOLD = 120 # seconds

def format_reminder_time(minutes: int) -> str:
    """Format the time to show in discord message."""
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    hours = minutes // 60
    remaining_minutes = minutes % 60

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
        self.sync_reminders.start()
        self.check_reminders.start()

    def cog_unload(self):
        self.sync_reminders.cancel()
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
            "The channel is not set up to receive reminders.",
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
                    name=f"Reminder will be sent to channel <#{reminder.channel_id}>" 
                        f" {reminder.reminder_minutes} minutes before the event",
                    value=(
                    f"Event id: {reminder.event_id}\n"
                    f"Event name: {reminder.event_name}\n"
                    f"Text: {reminder.text}\n"
                    f"url: {reminder.url}\n"
                    f"Event time: <t:{reminder.event_start}:F>\n\n"
                    ),
                    inline=False,
            )

        await interaction.followup.send(embed=embed)


    def create_default_reminders(self, event):
        now = int(time.time())
        channels = self.db_service.get_reminder_channels()

        start_time = int(event.start_time.timestamp())

        if not channels:
            logger.debug("No channels are set for reminders")
            return
        
        channels_ids = [channel.id for channel in channels]

        for time_reminder in DEFAULT_REMINDERS:
            # if the event will start in less time than the default reminder minutes
            # just continue do not create the reminder
            # Include the REMINDER_THRESHOLD to avoid creating new remainder 
            # that could be already sent 
            if time_reminder * 60 + REMINDER_THRESHOLD >= (start_time - now) :
                continue

            for channel_id in channels_ids:
                logger.debug(f"Creating reminders for {event.id}, {event.name} in channel: {channel_id}")
                reminder = self.db_service.create_reminder(
                    event_id=event.id,
                    event_name=event.name,
                    url=event.url,
                    text=event.description or "", # Check if a description could be the reminder text
                    channel_id=channel_id,
                    reminder_minutes=time_reminder,
                    event_start=start_time
                )
                if not reminder:
                    logger.debug(f"Creating reminders for {event.id}, {event.name} failed.")

    @tasks.loop(minutes=30)
    async def sync_reminders(self):
        
        channels = self.db_service.get_reminder_channels()
        if not channels:
            logger.debug("No channels are set for reminders")
            return
        
        # get reminder channels
        now = int(time.time())
        guild = self.bot.get_channel(self.bot.feature_forum_channel_id).guild
        events = await guild.fetch_scheduled_events(with_counts=False)

        events_by_id = {
            int(event.id): event
            for event in events
            if event.status not in (
                discord.EventStatus.completed,
                discord.EventStatus.cancelled,
                discord.EventStatus.active
            )
            and event.start_time.timestamp() > now
        }

        reminders = self.db_service.get_unsent_reminders()

        reminders_by_event = {}
        for reminder in reminders:
            if reminder.id not in reminders_by_event:
                reminders_by_event[reminder.id]  = []
            reminders_by_event[reminder.id].append(reminder)

        # Remove reminders with deleted events
        for event_id in reminders_by_event.keys():
            if event_id not in events_by_id:
                self.db_service.delete_reminders_for_event(event_id)

        # Check if the event has been not changed
        for event_id, reminders in reminders_by_event.items():
            # Check if the event_id in in the discord events
            # If not this event was removed in the lines above
            event = events_by_id.get(event_id)
            if event is None:
                continue
            start_time = int(event.start_time.timestamp())
            url = event.url
            name = event.name
            # description = event.description # Add description as a text reminder?

            # all reminders belongs to the event
            for reminder in reminders:
                if (reminder.event_name != event.name or
                    reminder.url != event.url or
                    reminder.event_start != start_time):

                    updated_reminders = self.db_service.update_reminder_for_event(
                        event_id, 
                        name,url,
                        start_time
                        )

                    if updated_reminders:
                        logger.debug(f"Updated reminders : {len(updated_reminders)}")
                    else:
                        logger.debug("No reminders were updated")
                    break

        # create for new events
        for event_id, event in events_by_id.items():
            if event_id in reminders_by_event:
                continue
            self.create_default_reminders(event)
    # TODO: remove reminders if the channel has been removed

    @sync_reminders.before_loop
    async def before_sync_reminders(self):
        await self.bot.wait_until_ready()

    async def send_reminder(self, reminder: Reminder) -> bool:
        try:
            channel = await self.bot.fetch_channel(reminder.channel_id)
        except Exception as e:
            logger.error(
                f"Reminder channel {reminder.channel_id} was not found: {e}"
            )
            return False

        # Calculate the minutes before de event
        left_minutes = (reminder.event_start - int(time.time()))//60
        time_text = format_reminder_time(left_minutes) 

        embed = discord.Embed(
            title="🔔 Event reminder",
            description=(
                f"**{reminder.event_name}**\n\n"
                f"{(reminder.text + '\n\n') if reminder.text else ''}"
                f"⏰ Starts in **{time_text}**.\n\n"
                f"<t:{reminder.event_start}:F>\n\n"
            ),
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="🔗 Event url",
            value=reminder.url
        )

        await channel.send(embed=embed)

        return True

    @tasks.loop(seconds=60)
    async def check_reminders(self):
        logger.debug("Checking reminders")
        reminders = self.db_service.get_pending_reminders()
        now = int(time.time()) # get the now timestamp in abs seconds
        
        for reminder in reminders:
            reminder_seconds = reminder.reminder_minutes*60
            
            if abs(reminder.event_start - now - reminder_seconds) < REMINDER_THRESHOLD:
                try: 
                    sent = await self.send_reminder(reminder)
                    if sent:
                        self.db_service.mark_reminder_sent(
                            reminder.id,
                            now,
                        )
                        logger.debug(f"Reminder has been sent: {reminder.id} | Event: {reminder.event_name} | Channel id {reminder.channel_id}")
                except Exception as e:
                    logger.exception(
                        f"Failed to send reminder {reminder.id}: {e}"
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
    async def change_reminder_text(self, interaction: discord.Interaction, event_id: str, text: str):
        await interaction.response.defer(ephemeral=True)
        # Using string for event_id due that event id have around 20 digits and it is too large for int type in discord ui
        if len(event_id) > 25:
            await interaction.followup.send("Event id too large.")
            return
    
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
                name=f"Reminder id {reminder.id}",
                value=(
                    f"**Event:** {reminder.event_name}\n"
                    f"**Channel ID:** {reminder.channel_id}\n"
                    f"**Reminder:** {reminder.reminder_minutes} minutes before the event\n"
                    f"**Text:** {reminder.text}"
                ),
                inline=False,
            )

        await interaction.followup.send(embed=embed)

    @commands.Cog.listener()
    async def on_scheduled_event_update(
        self,
        before: discord.ScheduledEvent,
        after: discord.ScheduledEvent,
    ):
        logger.debug(f"Scheduled event updated: {after.id}")

        updated_reminders = self.db_service.update_reminder_for_event(
            event_id = before.id, 
            name=after.name,
            url=after.url,
            start_time=int(after.start_time.timestamp())
            )
        
        if updated_reminders:
            logger.debug(f"Updated reminders : {len(updated_reminders)}")
            return
        
        logger.debug("No reminders were updated")


    @commands.Cog.listener()
    async def on_scheduled_event_delete(
        self,
        event: discord.ScheduledEvent,
    ):
        removed_event = self.db_service.delete_reminders_for_event(event.id)

        if removed_event:
            logger.debug(f"Scheduled event deleted from remiders: {event.id}")
            return

        logger.debug(f"Failed to remove scheduled event from remiders: {event.id}")


    @commands.Cog.listener()
    async def on_scheduled_event_create(
        self,
        event: discord.ScheduledEvent,
    ):
        try:
            self.create_default_reminders(event)
            logger.debug(f"Scheduled event '{event.name}' created, event id: {event.id}")
        except Exception as e:
            logger.error(f"An error ocurred during reminder creation for event {event.id}: {event.name} | {e}")


async def setup(bot: ByteBot):
    await bot.add_cog(ReminderCog(bot))

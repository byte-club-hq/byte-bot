import logging
import time
import discord
from discord import app_commands
from discord.ext import commands, tasks
import os

from byte_bot.byte_bot import ByteBot
from byte_bot.services.reminder_service import ReminderService, Reminder

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

REMINDER_CHECK_LOOP_TIME = int(os.getenv("REMINDER_CHECK_LOOP_TIME", 60))  # in seconds
SYNC_REMINDER_LOOP_TIME = int(os.getenv("SYNC_REMINDER_LOOP_TIME", 30))  # in minutes
REMINDER_TIME_THRESHOLD = int(os.getenv("REMINDER_TIME_THRESHOLD", 120))  # in seconds
REMINDER_TIMES_BEFORE_EVENT = [
    int(minutes) for minutes in os.getenv("REMINDER_TIMES_BEFORE_EVENT", "10,1440").split(",")
]

use_default_rules_env = os.getenv("USE_DEFAULT_REMINDER_RULES", "true").lower()
USE_DEFAULT_REMINDER_RULES = use_default_rules_env in ("true", "1")

default_channel = os.getenv("DEFAULT_REMINDER_CHANNEL")
DEFAULT_REMINDER_CHANNEL = int(default_channel) if default_channel else None


def format_reminder_time(minutes: int) -> str:
    """Format the time to show in discord message."""
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"

    return f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"


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
            name="list_events",
            description="List upcoming events"
    )
    @app_commands.guild_only()
    async def list_events(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild

        if guild is None:
            return

        logger.debug("Fetching scheduled events ...")
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
                    f"Event id: {event.id}"
                    f"⏱️ <t:{timestamp}:F>\n"
                    f"🔗 {event.url}\n\n"
                 ),
                 inline=False,
            )

        await interaction.followup.send(embed=embed)

    @reminder.command(name="list_rules_by_event", description="List rule reminder for an event (Use event_id)")
    @app_commands.guild_only()
    async def list_rules_by_event(self, interaction: discord.Interaction, event_id: str):
        await interaction.response.defer()
        guild = interaction.guild

        # Check if the event exists
        try: 
            event = await guild.fetch_scheduled_event(int(event_id))
        except Exception as e:
            logger.warning(f"Failed to fetch event : {event_id}")
            event = None

        if not event:
            await interaction.followup.send(f"Failed to get event with id: {event_id} does not exists.")
            return
        
        logger.debug("Fetching rules reminder ...")
        rules = self.db_service.get_reminders_rules_by_event(int(event_id))

        if not rules:
            await interaction.followup.send(
                f"There is no rule reminder for the event: {event_id}",
                ephemeral=True,
            )
            return
        
        embed = discord.Embed(
            title=f"📏 Rules for the event: {event_id}",
            color=discord.Color.dark_blue(),
        )

        for rule in rules:
            embed.add_field(
                name=f"Rule reminder id: {rule.id}",
                value=(
                f"# channel: <#{rule.channel_id}>"
                f"⏱️ minutes before: {rule.minutes_before}\n"
                f"📄 text: {rule.text}\n\n"
                ),
                inline=False,
            )

        await interaction.followup.send(embed=embed)

    @reminder.command(name="create_rule", description="Create a new rule reminder for event.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def create_rule(
        self, 
        interaction: discord.Interaction,
        event_id: str,
        channel: discord.TextChannel,
        minutes_before: int,
        text: str):

        await interaction.response.defer()
        guild = interaction.guild

        # Check if the event exists
        try: 
            event = await guild.fetch_scheduled_event(int(event_id))
        except Exception as e:
            logger.warning(f"Failed to fetch event : {event_id}")
            event = None

        if not event:
            await interaction.followup.send(f"Failed to get event with id: {event_id} does not exists.")
            return
        
        new_rule = self.db_service.create_reminder_rule(event_id, channel.id, minutes_before, text)

        if not new_rule:
            await interaction.followup.send(f"Failed to create a rule for event id: {event_id}.")
            return
        
        # Create a reminder given the rule
        self.create_reminder(new_rule, event)

        embed = discord.Embed(
            title="📏 A new rule reminder was created ...",
            color=discord.Color.dark_blue(),
        )
        
        embed.add_field(
            name=f"Rule reminder id: {new_rule.id}>",
            value=(
                f"Event id: {new_rule.event_id}\n"
                f"# channel: <#{new_rule.channel_id}>\n"
                f"⏱️ minutes before: {new_rule.minutes_before}\n"
                f"📄 text: {new_rule.text}\n"
            ),
            inline=False,
        )

        await interaction.followup.send(embed=embed)

    @reminder.command(name="remove_rule", description="Remove a rule reminder.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def remove_rule(self, interaction: discord.Interaction, rule_id: int):
        logger.debug(f"Removing rule: {rule_id}")
        now = int(time.time())
        removed_rule = self.db_service.remove_rule(rule_id, now)
        
        if not removed_rule:
            await interaction.followup.send(f"Failed to rule: {rule_id}. Check the rule_id")
            return
        
        await interaction.followup.send(f"Success removing rule: {rule_id}.")

    @reminder.command(name="list_reminders", description="List event reminders")
    @app_commands.guild_only()
    async def list_reminders(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild

        if guild is None:
            return

        reminders = self.db_service.get_unsent_reminders()

        if len(reminders) == 0:
            await interaction.followup.send(
                embed=discord.Embed(title="No reminders are set", description="You can add a reminder using")
            )
            return

        embed = discord.Embed(
            title="Reminders are the following",
            color=discord.Color.dark_blue(),
        )

        for reminder in reminders:
            embed.add_field(
                name=f"Reminder will be sent to channel <#{reminder.channel_id}>"
                f" at <t:{reminder.scheduled_at}:F>",
                value=(
                    f"Event id: {reminder.event_id}\n"
                    f"rule id: {reminder.rule_id}\n"
                    f"Event name: {reminder.event_name}\n"
                    f"Text: {reminder.description}"
                    f"url: {reminder.url}\n"
                    f"Event time: <t:{reminder.event_start}:F>\n\n"
                ),
                inline=False,
            )

        await interaction.followup.send(embed=embed)

    def create_reminder(self, rule, event):
        event_start = int(event.start_time.timestamp())
        scheduled_at = event_start - (rule.minutes_before * 60)
        description = rule.text or event.description
        now = int(time.time())

        # Do not create reminder if event will start in less time than minutes before
        if rule.minutes_before * 60 + REMINDER_TIME_THRESHOLD >= (event_start - now):
            logger.debug()
            return
        
        new_reminder = self.db_service.create_reminder(
            event_id=event.id,
            rule_id=rule.id,
            channel_id=rule.channel_id,
            event_name=event.name,
            url=event.url,
            description=description,
            event_start=event_start,
            scheduled_at=scheduled_at,
        )

        if new_reminder is None:
            logger.error(f"Reminder for the rule {rule.id} was not created.")

        logger.debug(
            f"New reminder (id: {new_reminder.id}) created for the event: {event.name} with the rule {rule.id}"
        )


    def create_default_rules_reminders(self, event):
        new_rules = []
        if not DEFAULT_REMINDER_CHANNEL:
            return
        rules_to_create = []
        for time_before in REMINDER_TIMES_BEFORE_EVENT:
            rules_to_create.append((
                int(event.id),
                DEFAULT_REMINDER_CHANNEL,
                time_before,
                None,
            ))
        new_rules = self.db_service.create_reminders_rules(rules_to_create)

        logger.debug(f"{len(new_rules)} have been created")

    def sync_events_w_reminders(self, reminders_by_event, events_by_id):
        for event_id, reminders in reminders_by_event.items():
            # Check if the event_id in in the discord events
            # If not this event was removed in the lines above
            event = events_by_id.get(event_id)

            if event is None:
                continue

            actual_start_time = int(event.start_time.timestamp())
            url = event.url
            name = event.name

            event_changed = any(
                reminder.event_name != event.name
                or reminder.url != event.url
                or reminder.event_start != actual_start_time
                for reminder in reminders
            )

            if not event_changed:
                continue

            # Update reminders because changed event
            updated_reminders = self.db_service.update_reminders_for_event(
                event_id=event_id, 
                name=name, 
                url=url, 
                start_time=actual_start_time,
            )

            if updated_reminders:
                logger.debug(f"Updated reminders : {len(updated_reminders)} for {name}")
            else:
                logger.debug("No reminders were updated")

    @tasks.loop(minutes=SYNC_REMINDER_LOOP_TIME)
    async def sync_reminders(self):
        # Getting events
        now = int(time.time())
        guild = self.bot.get_channel(self.bot.feature_forum_channel_id).guild
        events = await guild.fetch_scheduled_events(with_counts=False)

        # event_by_id stores {event_id: event}
        events_by_id = {
            int(event.id): event
            for event in events
            if (
                event.status
                not in (
                    discord.EventStatus.completed,
                    discord.EventStatus.cancelled,
                    discord.EventStatus.active,
                    )
                and event.start_time.timestamp() > now
            )
        }

        # get reminder rules
        rules = self.db_service.get_reminders_rules()

        # rules_by_event stores {event_id: [rule1, rule2 ...]}
        rules_by_event = {}

        for rule in rules:
            if rule.event_id not in rules_by_event:
                rules_by_event[int(rule.event_id)] = []
            rules_by_event[int(rule.event_id)].append(rule)

        # Cancel reminders and remove rules for deleted events
        for event_id in rules_by_event.keys():
            if event_id not in events_by_id:
                self.db_service.remove_rules_for_event(event_id, now)

        # Notes: I could be good to remove rules with deleted channels
        # But for now if the channel does not exists the send_reminder function
        # will throw a message indicating that channel does not exist
        # and mark that reminder as canceled
        # TODO: Remove all rules and reminder related with deleted channels

        # get reminders
        reminders = self.db_service.get_unsent_reminders()

        # Cancel past reminders
        self.db_service.cancel_expired_reminders(now)

        # reminders_by_event stores {event_id: [reminder1, reminder2 ...]}
        reminders_by_event = {}
        for reminder in reminders:
            if reminder.event_start <= now:
                continue

            if reminder.event_id not in reminders_by_event:
                reminders_by_event[int(reminder.event_id)] = []

            reminders_by_event[int(reminder.event_id)].append(reminder)

        # Create new rules ?
        if USE_DEFAULT_REMINDER_RULES:
            for event_id, event in events_by_id.items():
                # check if there no rule for event_id
                if event_id not in rules_by_event:
                    self.create_default_rules_reminders(event)

        self.sync_events_w_reminders(reminders_by_event, events_by_id)

        reminders = self.db_service.get_unsent_reminders()
        reminder_rule_ids = {reminder.rule_id for reminder in reminders}

        rules = self.db_service.get_reminders_rules()

        for rule in rules:
            if rule.id in reminder_rule_ids:
                continue
            event = events_by_id.get(rule.event_id)

            if event is None:
                continue

            self.create_reminder(rule, event)


    @sync_reminders.before_loop
    async def before_sync_reminders(self):
        await self.bot.wait_until_ready()

    async def send_reminder(self, reminder: Reminder) -> bool:
        try:
            # If the channel is not found the line above will raise an error
            channel = await self.bot.fetch_channel(reminder.channel_id)
            
        except Exception as e:
            logger.error(f"Reminder channel {reminder.channel_id} was not found: {e}")
            now = int(time.time())
            self.db_service.cancel_reminder(reminder.id, now)
            return False

        # Calculate the minutes before de event
        left_minutes = (reminder.event_start - int(time.time())) // 60
        time_text = format_reminder_time(left_minutes)

        embed = discord.Embed(
            title="🔔 Event reminder",
            description=(
                f"**{reminder.event_name}**\n\n"
                f"{(reminder.description + '\n\n') if reminder.description else ''}"
                f"⏰ Starts in **{time_text}**.\n\n"
                f"<t:{reminder.event_start}:F>\n\n"
            ),
            color=discord.Color.blurple(),
        )

        embed.add_field(name="🔗 Event url", value=reminder.url)

        await channel.send(embed=embed)

        return True

    @tasks.loop(seconds=REMINDER_CHECK_LOOP_TIME)
    async def check_reminders(self):
        logger.debug("Checking reminders")
        reminders = self.db_service.get_unsent_reminders()
        now = int(time.time())  # get the now timestamp in abs seconds

        for reminder in reminders:
            if abs(reminder.scheduled_at - now) < REMINDER_TIME_THRESHOLD:
                try:
                    sent = await self.send_reminder(reminder)
                    if sent:
                        self.db_service.mark_reminder_sent(
                            reminder.id,
                            now,
                        )
                        logger.debug(
                            f"Reminder has been sent: {reminder.id} | Event: {reminder.event_name} | Channel id {reminder.channel_id}"
                        )
                except Exception as e:
                    logger.exception(f"Failed to send reminder {reminder.id}: {e}")

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_scheduled_event_update(
        self,
        before: discord.ScheduledEvent,
        after: discord.ScheduledEvent,
    ):
        logger.debug(f"Scheduled event updated: {after.id} | {after.name}")
        updated_reminders = self.db_service.update_reminders_for_event(
            event_id=before.id,
            name=after.name,
            url=after.url,
            start_time=int(after.start_time.timestamp()),
        )

        if updated_reminders:
            logger.debug(f"Updated reminders : {len(updated_reminders)} for {after.name}")
            return

        logger.debug("No reminders were updated")

    @commands.Cog.listener()
    async def on_scheduled_event_delete(
        self,
        event: discord.ScheduledEvent,
    ):
        now = int(time.time())
        removed_event = self.db_service.remove_rules_for_event(event.id, now)

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
            logger.debug(f"Scheduled event '{event.name}' created, event id: {event.id}")

            if USE_DEFAULT_REMINDER_RULES:
                new_rules = self.create_default_rules_reminders(event)

                for rule in new_rules:
                    self.create_reminder(rule, event)

                logger.debug(f"Default reminders were created for '{event.name}' | event id: {event.id}")

        except Exception as e:
            logger.error(f"An error ocurred during reminder creation for event {event.id}: {event.name} | {e}")


async def setup(bot: ByteBot):
    await bot.add_cog(ReminderCog(bot))

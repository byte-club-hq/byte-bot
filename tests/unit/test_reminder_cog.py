from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import time
import discord
import pytest

from byte_bot.cogs.reminder import ReminderCog


@pytest.fixture
def cog():
    """Create a ReminderCog with a mocked ReminderService."""
    bot = MagicMock()

    cog = ReminderCog(bot)

    cog.db_service = MagicMock()

    return cog


def make_event(
    event_id=123,
    name="Test event",
    url="https://example.com/event",
    start_time=None,
    status=discord.EventStatus.scheduled,
):
    if start_time is None:
        start_time = datetime.now(timezone.utc) + timedelta(hours=2)

    return SimpleNamespace(
        id=event_id,
        name=name,
        url=url,
        start_time=start_time,
        status=status,
        description="Event description",
    )


def make_rule(
    rule_id=1,
    event_id=123,
    channel_id=456,
    minutes_before=10,
    text="Reminder text",
):
    return SimpleNamespace(
        id=rule_id,
        event_id=event_id,
        channel_id=channel_id,
        minutes_before=minutes_before,
        text=text,
    )


def make_reminder(
    reminder_id=1,
    event_id=123,
    rule_id=1,
    channel_id=456,
    event_name="Test event",
    url="https://example.com/event",
    description="Reminder",
    event_start=2_000,
    scheduled_at=1_400,
):
    return SimpleNamespace(
        id=reminder_id,
        event_id=event_id,
        rule_id=rule_id,
        channel_id=channel_id,
        event_name=event_name,
        url=url,
        description=description,
        event_start=event_start,
        scheduled_at=scheduled_at,
    )


def test_create_reminder_does_not_create_when_event_is_too_close(cog):
    rule = make_rule(minutes_before=30)

    event_start = 1_000
    event = make_event(start_time=datetime.fromtimestamp(event_start, tz=timezone.utc))

    # Event starts in 10 minutes, but the rule requires 30 minutes.
    with patch("byte_bot.cogs.reminder.time.time", return_value=400):
        cog.create_reminder(rule, event)

    cog.db_service.create_reminder.assert_not_called()


def test_create_reminder_creates_reminder(cog):
    rule = make_rule(
        rule_id=10,
        event_id=123,
        channel_id=456,
        minutes_before=30,
        text="Custom reminder",
    )

    event_start = int(time.time()) + 24 * 60 * 60
    event = make_event(
        event_id=123,
        name="My event",
        url="https://example.com",
        start_time=datetime.fromtimestamp(event_start, tz=timezone.utc),
    )

    cog.db_service.create_reminder.return_value = SimpleNamespace(id=99)

    with patch("byte_bot.cogs.reminder.time.time", return_value=500):
        cog.create_reminder(rule, event)

    cog.db_service.create_reminder.assert_called_once_with(
        event_id=123,
        rule_id=10,
        channel_id=456,
        event_name="My event",
        url="https://example.com",
        description="Custom reminder",
        event_start=event_start,
        scheduled_at=event_start - (30 * 60),
    )


def test_create_reminder_uses_event_description_when_rule_text_is_none(cog):
    rule = make_rule(text=None)

    event_start = 2_000
    event = make_event(start_time=datetime.fromtimestamp(event_start, tz=timezone.utc))
    event.description = "Description from Discord event"

    cog.db_service.create_reminder.return_value = SimpleNamespace(id=99)

    with patch("byte_bot.cogs.reminder.time.time", return_value=500):
        cog.create_reminder(rule, event)

    assert cog.db_service.create_reminder.call_args.kwargs["description"] == "Description from Discord event"


def test_sync_events_does_nothing_when_event_has_not_changed(cog):
    event_start = 2_000

    event = make_event(
        event_id=123,
        name="Test event",
        url="https://example.com",
        start_time=datetime.fromtimestamp(event_start, tz=timezone.utc),
    )

    reminder = make_reminder(
        event_id=123,
        event_name="Test event",
        url="https://example.com",
        event_start=event_start,
    )

    cog.sync_events_w_reminders(
        reminders_by_event={123: [reminder]},
        events_by_id={123: event},
    )

    cog.db_service.update_reminders_for_event.assert_not_called()


def test_sync_events_updates_when_event_changes(cog):
    event_start = 2_000

    event = make_event(
        event_id=123,
        name="New event name",
        url="https://example.com",
        start_time=datetime.fromtimestamp(event_start, tz=timezone.utc),
    )

    reminder = make_reminder(
        event_id=123,
        event_name="Old event name",
        url="https://example.com",
        event_start=event_start,
    )

    cog.db_service.update_reminders_for_event.return_value = [reminder]

    cog.sync_events_w_reminders(
        reminders_by_event={123: [reminder]},
        events_by_id={123: event},
    )

    cog.db_service.update_reminders_for_event.assert_called_once_with(
        event_id=123,
        name="New event name",
        url="https://example.com",
        start_time=event_start,
    )


def test_sync_events_ignores_missing_event(cog):
    reminder = make_reminder(event_id=123)

    cog.sync_events_w_reminders(
        reminders_by_event={123: [reminder]},
        events_by_id={},
    )

    cog.db_service.update_reminders_for_event.assert_not_called()


@pytest.mark.asyncio
async def test_event_update_removes_rules_when_event_is_cancelled(cog):
    before = make_event(
        status=discord.EventStatus.scheduled,
    )
    after = make_event(
        status=discord.EventStatus.cancelled,
    )

    with patch("byte_bot.cogs.reminder.time.time", return_value=500):
        await cog.on_scheduled_event_update(before, after)

    cog.db_service.remove_rules_for_event.assert_called_once_with(
        before.id,
        500,
    )

    cog.db_service.update_reminders_for_event.assert_not_called()


@pytest.mark.asyncio
async def test_event_update_does_nothing_when_nothing_changed(cog):
    start_time = datetime.now(timezone.utc) + timedelta(hours=2)

    before = make_event(
        name="Test event",
        url="https://example.com",
        start_time=start_time,
    )

    after = make_event(
        name="Test event",
        url="https://example.com",
        start_time=start_time,
    )

    await cog.on_scheduled_event_update(before, after)

    cog.db_service.update_reminders_for_event.assert_not_called()
    cog.db_service.remove_rules_for_event.assert_not_called()
    cog.db_service.cancel_reminders_for_event.assert_not_called()


@pytest.mark.asyncio
async def test_event_update_updates_reminders_when_event_changes(cog):
    start_time = datetime.now(timezone.utc) + timedelta(hours=2)

    before = make_event(
        event_id=123,
        name="Old name",
        url="https://example.com",
        start_time=start_time,
    )

    after = make_event(
        event_id=123,
        name="New name",
        url="https://example.com",
        start_time=start_time,
    )

    cog.db_service.update_reminders_for_event.return_value = [MagicMock()]

    await cog.on_scheduled_event_update(before, after)

    cog.db_service.update_reminders_for_event.assert_called_once_with(
        event_id=123,
        name="New name",
        url="https://example.com",
        start_time=int(start_time.timestamp()),
    )

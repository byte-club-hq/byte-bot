from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import time
import discord
import pytest

from byte_bot.cogs.reminder import ReminderCog, snowflake_to_timestamp

from byte_bot.cogs.reminder import (
    get_formatted_events,
    CANCELED_EVENT,
    SCHEDULED_EVENT,
)

def datetime_to_snowflake(dt: datetime) -> str:
    """Generate a Discord snowflake for a given UTC datetime."""
    discord_epoch = 1420070400000
    timestamp_ms = int(dt.timestamp() * 1000)

    return str((timestamp_ms - discord_epoch) << 22)

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


@pytest.fixture
def recurring_event():
    original_start = "2026-11-16T18:00:00+00:00"

    return {
        "id": "1444045695198957619",
        "guild_id": "123456789",
        "name": "Weekly meeting",
        "description": "Weekly team meeting",
        "scheduled_start_time": original_start,
        "status": SCHEDULED_EVENT,
        "recurrence_rule": {
            "start": original_start,
            "frequency": 2,
            "interval": 1,
        },
        "guild_scheduled_event_exceptions": [],
    }


def test_cancelled_recurring_event_occurrence(recurring_event):
    """A cancelled occurrence should be marked as cancelled. 
    Only for the cancelled event. Not cancelling the whole recurrent event"""

    recurring_event["guild_scheduled_event_exceptions"] = [
        {
            "event_exception_id": str(
                # Snowflake corresponding to the original occurrence
                1449128676556800000
            ),
            "scheduled_start_time": None,
            "scheduled_end_time": None,
            "is_canceled": True,
        }
    ]

    recurring_event["scheduled_start_time"] = (
        "2026-11-16T18:00:00+00:00"
    )

    exception_id = str(
        (int(recurring_event["scheduled_start_time"].replace(
            "-", ""
        )[:0] or 0))
    ) if False else None

    # The exception must identify the original occurrence.
    # We construct the snowflake from its Unix timestamp.

    timestamp = int(
        datetime.fromisoformat(
            recurring_event["scheduled_start_time"]
        ).timestamp()
    )

    exception_id = str(
        ((timestamp * 1000 - 1420070400000) << 22)
    )

    recurring_event["guild_scheduled_event_exceptions"][0][
        "event_exception_id"
    ] = exception_id

    event = get_formatted_events([recurring_event])[0]

    assert event.is_recurring is True
    assert event.status == CANCELED_EVENT
    assert event.is_cancelled is False


def test_cancelled_recurring_event_occurrence_all(recurring_event):
    """A cancelled event should be marked as cancelled."""

    recurring_event["status"] = CANCELED_EVENT

    event = get_formatted_events([recurring_event])[0]

    assert event.is_recurring is True
    assert event.status == CANCELED_EVENT
    assert event.is_cancelled is True

def test_recurring_event_occurrence_start_time_changed(recurring_event):
    """A modified occurrence should use its new scheduled start time."""

    original_start = int(
        datetime.fromisoformat(
            recurring_event["scheduled_start_time"]
        ).timestamp()
    )

    new_start = "2026-11-16T20:00:00+00:00"

    exception_id = str(
        ((original_start * 1000 - 1420070400000) << 22)
    )

    recurring_event["guild_scheduled_event_exceptions"] = [
        {
            "event_exception_id": exception_id,
            "scheduled_start_time": new_start,
            "scheduled_end_time": "2026-11-16T21:00:00+00:00",
            "is_canceled": False,
        }
    ]

    event = get_formatted_events([recurring_event])[0]

    expected_start = datetime.fromisoformat(new_start)

    assert event.is_recurring is True
    assert event.start_time == expected_start
    assert event.status == SCHEDULED_EVENT
    assert event.is_cancelled is False


def test_unrelated_exception_does_not_modify_event(recurring_event):

    original_start = datetime.fromisoformat(
        recurring_event["scheduled_start_time"]
    )

    unrelated_start = datetime(
        2026, 11, 23, 18, 0, tzinfo=timezone.utc
    )

    recurring_event["guild_scheduled_event_exceptions"] = [
        {
            "event_exception_id": datetime_to_snowflake(
                unrelated_start
            ),
            "scheduled_start_time": None,
            "scheduled_end_time": None,
            "is_canceled": True,
        }
    ]

    event = get_formatted_events([recurring_event])[0]

    assert event.start_time == original_start
    assert event.status == SCHEDULED_EVENT
    assert event.is_cancelled is False

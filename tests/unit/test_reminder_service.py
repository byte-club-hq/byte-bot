import pytest
import sqlite3

from byte_bot.cogs.reminder import format_reminder_time
from byte_bot.services.reminder_service import ReminderService

@pytest.mark.parametrize(
    "minutes, expected",
    [
        (0, "0 minutes"),
        (1, "1 minute"),
        (2, "2 minutes"),
        (59, "59 minutes"),
        (60, "1 hour"),
        (61, "1 hour 1 minute"),
        (62, "1 hour 2 minutes"),
        (119, "1 hour 59 minutes"),
        (120, "2 hours"),
        (121, "2 hours 1 minute"),
        (24 * 60, "24 hours"),
    ],
)
def test_format_reminder_time(minutes, expected):
    assert format_reminder_time(minutes) == expected


@pytest.fixture
def connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    connection.executescript("""
        CREATE TABLE reminders_rules (
            id INTEGER PRIMARY KEY,
            event_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            minutes_before INTEGER NOT NULL,
            text TEXT,
            UNIQUE (event_id, channel_id, minutes_before)
        );

        CREATE TABLE reminders (
            id INTEGER PRIMARY KEY,
            event_id INTEGER NOT NULL,
            rule_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            event_name TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            event_start INTEGER NOT NULL,
            scheduled_at INTEGER NOT NULL,
            sent_at INTEGER,
            canceled_at INTEGER
        );
    """)

    yield connection
    connection.close()

class FakeDatabaseService:
    def __init__(self, connection):
        self.connection = connection

    def get_connection(self):
        return self.connection

@pytest.fixture
def service(connection):
    db = FakeDatabaseService(connection)
    return ReminderService(db)

def test_create_reminder_rule(service):
    rule = service.create_reminder_rule(
        event_id=11,
        channel_id=12,
        minutes_before=15,
        text="Test message"
    )
    assert rule is not None
    assert rule.id == 1
    assert rule.event_id == 11
    assert rule.channel_id == 12
    assert rule.minutes_before == 15
    assert rule.text == "Test message"

def test_get_reminder_rules(service):
    service.create_reminder_rule(
        event_id=11,
        channel_id=12,
        minutes_before=15,
        text="Test message 15"
    )
    service.create_reminder_rule(
            event_id=11,
            channel_id=12,
            minutes_before=30,
            text="Test message 30"
        )

    rules = service.get_reminders_rules()

    assert len(rules) == 2
    assert rules[0].event_id == 11
    assert rules[0].channel_id == 12
    assert rules[1].minutes_before == 30
    assert rules[1].text == "Test message 30"

def test_get_reminder_rules_by_event(service):
    service.create_reminder_rule(
        event_id=100,
        channel_id=200,
        minutes_before=10,
        text="Event 100",
    )

    service.create_reminder_rule(
        event_id=200,
        channel_id=300,
        minutes_before=10,
        text="Event 200",
    )

    rules = service.get_reminders_rules_by_event(100)

    assert len(rules) == 1
    assert rules[0].event_id == 100

def test_get_reminder_rules_by_event_returns_empty_list(service):
    assert service.get_reminders_rules_by_event(999) == []

def test_create_reminder(service):
    reminder = service.create_reminder(
        event_id=123,
        rule_id=1,
        channel_id=456,
        event_name="My event",
        url="https://example.com",
        description="Some description",
        event_start=2000,
        scheduled_at=1400,
    )

    assert reminder is not None
    assert reminder.event_id == 123
    assert reminder.rule_id == 1
    assert reminder.channel_id == 456
    assert reminder.event_name == "My event"
    assert reminder.event_start == 2000
    assert reminder.scheduled_at == 1400
    assert reminder.sent_at is None
    assert reminder.canceled_at is None

def test_get_unsent_reminders(service):
    service.create_reminder(
        1, 1, 100, "Event", "url", "description", 2000, 1500
    )

    reminders = service.get_unsent_reminders()

    assert len(reminders) == 1
    assert reminders[0].sent_at is None
    assert reminders[0].canceled_at is None

def test_mark_reminder_sent(service):
    reminder = service.create_reminder(
        1, 1, 100, "Event", "url", "description", 2000, 1500
    )

    updated = service.mark_reminder_sent(
        reminder.id,
        timestamp=1600,
    )

    assert updated is not None
    assert updated.sent_at == 1600

def test_sent_reminder_is_not_unsent(service):
    reminder = service.create_reminder(
        1, 1, 100, "Event", "url", "description", 2000, 1500
    )

    service.mark_reminder_sent(reminder.id, 1600)

    assert service.get_unsent_reminders() == []

def test_cancel_reminder(service):
    reminder = service.create_reminder(
        1, 1, 100, "Event", "url", "description", 2000, 1500
    )

    result = service.cancel_reminder(
        reminder.id,
        timestamp=1600,
    )

    assert result == 1

def test_canceled_reminder_is_not_unsent(service):
    reminder = service.create_reminder(
        1, 1, 100, "Event", "url", "description", 2000, 1500
    )

    service.cancel_reminder(reminder.id, 1600)

    assert service.get_unsent_reminders() == []

def test_cancel_expired_reminders(service):
    service.create_reminder(
        1, 1, 100, "Expired", "url", "", 900, 800
    )

    service.create_reminder(
        2, 2, 100, "Exactly now", "url", "", 1000, 900
    )

    service.create_reminder(
        3, 3, 100, "Future", "url", "", 1100, 1000
    )

    canceled = service.cancel_expired_reminders(1000)

    assert canceled == 2

    reminders = service.get_unsent_reminders()

    assert len(reminders) == 1
    assert reminders[0].event_id == 3

def test_update_reminders_for_event_preserves_offset(service):
    service.create_reminder(
        event_id=123,
        rule_id=1,
        channel_id=456,
        event_name="Old name",
        url="old-url",
        description="description",
        event_start=10_000,
        scheduled_at=9_400,
    )

    updated = service.update_reminders_for_event(
        event_id=123,
        name="New name",
        url="new-url",
        start_time=20_000,
    )

    assert len(updated) == 1

    reminder = updated[0]

    assert reminder.event_name == "New name"
    assert reminder.url == "new-url"
    assert reminder.event_start == 20_000
    assert reminder.scheduled_at == 19_400

def test_update_does_not_update_sent_reminders(service):
    reminder = service.create_reminder(
        123, 1, 456, "Old", "old", "", 10_000, 9_400
    )

    service.mark_reminder_sent(reminder.id, 9_500)

    updated = service.update_reminders_for_event(
        123,
        "New",
        "new",
        20_000,
    )

    assert updated == []

def test_remove_rule_removes_rule_and_cancels_reminders(service):
    rule = service.create_reminder_rule(
        123,
        456,
        10,
        "Reminder",
    )

    service.create_reminder(
        123,
        rule.id,
        456,
        "Event",
        "url",
        "",
        2000,
        1400,
    )

    result = service.remove_rule(rule.id, 1500)

    assert result is True
    assert service.get_reminders_rules_by_event(123) == []
    assert service.get_unsent_reminders() == []

def test_create_duplicate_reminder_rule_returns_none(service):
    first = service.create_reminder_rule(
        event_id=123,
        channel_id=456,
        minutes_before=10,
        text="First reminder",
    )

    second = service.create_reminder_rule(
        event_id=123,
        channel_id=456,
        minutes_before=10,
        text="Second reminder",
    )

    assert first is not None
    assert second is None

# Ensure that there is no duplicates in the combination
# of (event_id, channel_id, minutes_before)
def test_create_reminder_rules_allows_different_combinations(service):
    rule1 = service.create_reminder_rule(
        event_id=123,
        channel_id=456,
        minutes_before=10,
        text="Reminder 1",
    )

    rule2 = service.create_reminder_rule(
        event_id=123,
        channel_id=456,
        minutes_before=60,
        text="Reminder 2",
    )

    rule3 = service.create_reminder_rule(
        event_id=123,
        channel_id=789,
        minutes_before=10,
        text="Reminder 3",
    )

    rule4 = service.create_reminder_rule(
        event_id=999,
        channel_id=456,
        minutes_before=10,
        text="Reminder 4",
    )

    assert rule1 is not None
    assert rule2 is not None
    assert rule3 is not None
    assert rule4 is not None
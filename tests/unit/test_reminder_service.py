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
            text TEXT
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


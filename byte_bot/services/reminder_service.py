from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from byte_bot.services.database_service import DatabaseService

@dataclass
class ReminderRule:
    id: int
    event_id: int
    channel_id: int
    minutes_before: int
    text: str


@dataclass
class Reminder:
    id: int
    event_id: int
    rule_id: int
    channel_id: int
    event_name: str
    url: str
    description: str
    event_start: int
    scheduled_at: int
    sent_at: int | None
    canceled_at: int | None

REMINDER_COLUMNS = """
    id,
    event_id,
    rule_id,
    channel_id,
    event_name,
    url,
    description,
    event_start,
    scheduled_at,
    sent_at,
    canceled_at
"""

def row_to_rule(row: sqlite3.Row) -> ReminderRule:
    return ReminderRule(
        id=row["id"],
        event_id=row["event_id"],
        channel_id=row["channel_id"],
        minutes_before=row["minutes_before"],
        text=row["text"],
    )


# A helper function to transforms a sqlite row to Reminder dataclass type
def row_to_reminder(row: sqlite3.Row) -> Reminder:
    return Reminder(
        id=row["id"],
        event_id=row["event_id"],
        rule_id=row["rule_id"],
        channel_id=row["channel_id"],
        event_name=row["event_name"],
        url=row["url"],
        description=row["description"],
        event_start=row["event_start"],
        scheduled_at=row["scheduled_at"],
        sent_at=row["sent_at"],
        canceled_at=row["canceled_at"],
    )


class ReminderService:
    def __init__(self, database_service: DatabaseService):
        self.db = database_service

    def create_reminder(self, 
                        event_id,
                        rule_id,
                        channel_id,
                        event_name,
                        url,
                        description ,
                        event_start,
                        scheduled_at) -> Reminder | None:
        """Create a new reminder"""
        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    f"""
                    INSERT INTO reminders (
                        event_id,
                        rule_id,
                        channel_id,
                        event_name,
                        url,
                        description,
                        event_start,
                        scheduled_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING {REMINDER_COLUMNS}
                    """,
                    (
                        event_id,
                        rule_id,
                        channel_id,
                        event_name,
                        url,
                        description ,
                        event_start,
                        scheduled_at,
                    )
                )

                row = cursor.fetchone()

        if row is None:
            return None
        
        return row_to_reminder(row)

    def create_reminder_rule(self, event_id: int, channel_id: int, minutes_before: int, text: str) -> ReminderRule | None:
        """Create multiple reminders given a list of new data"""
        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO reminders_rules (
                        event_id,
                        channel_id,
                        minutes_before,
                        text
                    )
                    VALUES (?, ?, ?, ?)
                    RETURNING id, event_id, channel_id, minutes_before, text
                    """,
                    (
                        event_id,
                        channel_id,
                        minutes_before,
                        text,
                    )
                )

                row = cursor.fetchone()

        if row is None:
            return None

        return row_to_rule(row)
    
    def create_reminders_rules(self, rules: list[tuple]) -> list[ReminderRule]:
        """Create multiple reminders given a list of new data"""
        new_rules = []

        with self.db.get_connection() as connection:
            with connection:
                for rule in rules:
                    cursor = connection.execute(
                        """
                        INSERT INTO reminders_rules (
                            event_id,
                            channel_id,
                            minutes_before,
                            text
                        )
                        VALUES (?, ?, ?, ?)
                        RETURNING id, event_id, channel_id, minutes_before, text
                        """,
                        rule
                    )

                    row = cursor.fetchone()

                    if row:
                        new_rules.append(row_to_rule(row))

        return new_rules
    
    def get_unsent_reminders(self) -> list[Reminder]:
        """Return a list of reminders scheduled to be sent."""
        reminders = []
        with self.db.get_connection() as connection:
            rows = connection.execute(
                f"""
                SELECT {REMINDER_COLUMNS}
                FROM reminders
                WHERE sent_at IS NULL
                    AND canceled_at IS NULL
                """
            ).fetchall()

        if not rows:
            return reminders

        for row in rows:
            reminders.append(row_to_reminder(row))

        return reminders

    def mark_reminder_sent(
        self,
        reminder_id: int,
        timestamp: int,
    ) -> Reminder | None:
        """Mark a reminder as sent and return the updated reminder."""

        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    f"""
                    UPDATE reminders 
                    SET sent_at = ?
                    WHERE id = ?
                    RETURNING {REMINDER_COLUMNS}
                    """,
                    (
                        timestamp,
                        reminder_id,
                    ),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return row_to_reminder(row)
    
    def cancel_reminder(self, reminder_id: int, timestamp: int) -> int:
        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE reminders
                    SET 
                        sent_at = ?,
                        canceled_at = ?
                    WHERE reminder_id = ? 
                        AND sent_at IS NULL
                        AND canceled_at IS NULL
                    """,
                    (
                        0,
                        timestamp,
                        reminder_id,
                    ),
                )

        return cursor.rowcount
    
    def cancel_expired_reminders(self, timestamp: int) -> int:
        """Mark as canceled expired reminders"""
        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE reminders
                    SET 
                        sent_at = ?,
                        canceled_at = ?
                    WHERE sent_at IS NULL
                        AND canceled_at IS NULL
                        AND event_start <= ?
                    """,
                    (
                        0,
                        timestamp,
                        timestamp,
                    ),
                )

        return cursor.rowcount

    def cancel_reminder_by_rule(self, rule_id, timestamp) -> bool:
        """Mark canceled to a reminder given the rule id."""
        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE reminders
                    SET
                        sent_at = ?,
                        canceled_at = ?
                    WHERE rule_id = ?
                        AND sent_at IS NULL
                    """,
                    (0, timestamp, rule_id),
                )

        return cursor.rowcount > 0
    
    def cancel_reminders_for_event(self, event_id, timestamp) -> bool:
        """Mark canceled to a reminder given the event id."""
        with self.db.get_connection() as connection:
            with connection:
                # Set 0 to sent_at to avoid being NULL when canceled_at has a value
                # Therefore get_unsent_reminders will not consider canceled reminders
                cursor = connection.execute(
                    """
                    UPDATE reminders
                    SET
                        sent_at = ?,
                        canceled_at = ?
                    WHERE event_id = ?
                        AND sent_at IS NULL
                    """,
                    (0, timestamp, event_id),
                )

        return cursor.rowcount > 0


    def update_reminders_for_event(self, event_id, name, url, start_time):
        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    f"""
                    UPDATE reminders
                    SET 
                        event_name = ?,
                        url = ?,
                        event_start = ?,
                        scheduled_at = ? - (event_start - scheduled_at)
                    WHERE event_id = ?
                        AND sent_at IS NULL
                        AND canceled_at IS NULL
                    RETURNING {REMINDER_COLUMNS}
                        
                    """,
                    (
                        name,
                        url,
                        start_time,
                        start_time,
                        event_id
                    ),
                )

                rows = cursor.fetchall()

        return [
            row_to_reminder(row)
            for row in rows
        ]

    def remove_rule(self, rule_id: int, timestamp: int) -> bool:

        self.cancel_reminder_by_rule(rule_id, timestamp)

        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    DELETE FROM reminders_rules
                    WHERE id = ?
                    """,
                    (rule_id,),
                )

        return cursor.rowcount > 0
    
    def remove_rules_for_event(self, event_id, timestamp) -> bool:
        self.cancel_reminders_for_event(event_id, timestamp)

        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    DELETE FROM reminders_rules
                    WHERE event_id = ?
                    """,
                    (event_id,),
                )

        return cursor.rowcount > 0

    def get_reminders_rules_by_event(self, event_id: int) -> list[ReminderRule]:
        rules = []
        with self.db.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT 
                    id, 
                    event_id,
                    channel_id,
                    minutes_before,
                    text
                FROM reminders_rules
                WHERE event_id = ?
                """, 
                (event_id,),
            ).fetchall()

        if not rows:
            return rules

        for row in rows:
            rules.append(row_to_rule(row))

        return rules
    
    def get_reminders_rules(self) -> list[ReminderRule]:
        rules = []
        with self.db.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT 
                    id, 
                    event_id,
                    channel_id,
                    minutes_before,
                    text
                FROM reminders_rules
                """
            ).fetchall()

        if not rows:
            return rules

        for row in rows:
            rules.append(row_to_rule(row))

        return rules
        
from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from byte_bot.services.database_service import DatabaseService

@dataclass
class ReminderChannel:
    id: int
    name: str


@dataclass
class Reminder:
    id: int
    event_id: int
    event_name: str
    url: str
    text: str
    channel_id: int
    reminder_minutes: int
    event_start: int
    sent_at: int | None

# A helper function to tranforms a sqlite row to Reminder dataclass type
def row_to_reminder(row: sqlite3.Row) -> Reminder:
    return Reminder(
        id=row["id"],
        event_id=row["event_id"],
        event_name=row["event_name"],
        url=row["url"],
        text=row["text"],
        channel_id=row["channel_id"],
        reminder_minutes=row["reminder_minutes"],
        event_start=row["event_start"],
        sent_at=row["sent_at"],
    )

class ReminderService:
    def __init__(self, database_service: DatabaseService):
        self.db = database_service

    def get_reminder_channels(self) -> list[ReminderChannel]:
        """Return a list of all channels for reminder events."""
        channels = []
        with self.db.get_connection() as connection:
            rows = connection.execute("SELECT channel_id, name FROM reminder_channels").fetchall()

            if not rows:
                return channels

            for row in rows:
                channels.append(ReminderChannel(id=row[0], name=row[1]))

        return channels

    def set_channel_reminder(self, channel_id, name) -> ReminderChannel:
        """Add or update a channel used for event reminders."""
        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO reminder_channels (channel_id, name)
                    VALUES (?, ?)
                    ON CONFLICT(channel_id) DO UPDATE SET name = excluded.name
                    RETURNING channel_id, name
                    """,
                    (channel_id, name),
                )
                row = cursor.fetchone()

        return ReminderChannel(
            id=row["channel_id"],
            name=row["name"],
        )

    def remove_reminder_channel(self, channel_id) -> bool:
        """Remove a channel from the reminder channel table given the id."""
        with self.db.get_connection() as connection:
            with connection:
                connection.execute(
                    """
                        DELETE FROM reminders
                        WHERE channel_id = ?                    
                    """,
                    (channel_id,),
                )

                cursor = connection.execute(
                    """
                        DELETE FROM reminder_channels
                        WHERE channel_id = ?
                        """,
                    (channel_id,),
                )
        
        return cursor.rowcount > 0

    def get_pending_reminders(self) -> list[Reminder]:
        """Return a list of reminders scheduled to be sent."""
        reminders = []
        # Notes it coulp happen that an reminder has not been sent because
        # an error it could be good to add a filter event_start > now
        # in the sql query, but for now I guess this part is solved with the condition 
        # 0 < reminder.event_start - now <= reminder_seconds
        # in the calling function process_reminder, but I'm not sure
        with self.db.get_connection() as connection:
            rows = connection.execute(
                """
                SELECT 
                    id, 
                    event_id, 
                    event_name, 
                    url, 
                    text, 
                    channel_id, 
                    reminder_minutes, 
                    event_start,
                    sent_at
                FROM reminders
                WHERE sent_at IS NULL
                """
            ).fetchall()

        if not rows:
            return reminders

        for row in rows:
            reminders.append(row_to_reminder(row))

        return reminders

    def create_reminder(
        self,
        event_id: int,
        event_name: str,
        url: str,
        text: str,
        channel_id: int,
        reminder_minutes: int,
        event_start: int,
    ) -> Reminder | None:
        """Create and return a new envent reminder and return de updated reminder."""

        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO reminders (
                        event_id,
                        event_name,
                        url,
                        text,
                        channel_id,
                        reminder_minutes,
                        event_start,
                        sent_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING id, event_id, event_name, url, text,
                            channel_id, reminder_minutes, event_start, sent_at
                    """,
                    (
                        event_id,
                        event_name,
                        url,
                        text,
                        channel_id,
                        reminder_minutes,
                        event_start,
                        None,
                    ),
                )

                row = cursor.fetchone()

        if row is None:
            return None
        
        return row_to_reminder(row)
            

    def mark_reminder_sent(
        self,
        reminder_id: int,
        timestamp: int,
    ) -> Reminder | None:
        """Mark a reminder as sent and return the updated reminder."""

        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                        UPDATE reminders 
                        SET sent_at = ?
                        WHERE id = ?
                        RETURNING
                            id,
                            event_id,
                            event_name,
                            url,
                            text,
                            channel_id,
                            reminder_minutes,
                            event_start,
                            sent_at
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

    def update_reminder_start_time(self, event_id: int, timestamp: int) -> list[Reminder]:
        """Update start time for unsent reminders given an event id."""

        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE reminders
                    SET event_start = ?
                    WHERE event_id = ?
                        AND sent_at IS NULL
                    RETURNING
                        id,
                        event_id,
                        event_name,
                        url,
                        text,
                        channel_id,
                        reminder_minutes,
                        event_start,
                        sent_at
                    """,
                    (
                        timestamp,
                        event_id,
                    ),
                )

                rows = cursor.fetchall()
        
        return [
            row_to_reminder(row)
            for row in rows
        ]

    def update_reminder_text(self, event_id: int, text: str) -> list[Reminder]:
        """Update text for unsent reminders given an event id."""

        with self.db.get_connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE reminders
                    SET text = ?
                    WHERE event_id = ?
                        AND sent_at IS NULL
                    RETURNING
                        id,
                        event_id,
                        event_name,
                        url,
                        text,
                        channel_id,
                        reminder_minutes,
                        event_start,
                        sent_at
                    """,
                    (
                        text,
                        event_id,
                    ),
                )

                rows = cursor.fetchall()

        return [
            row_to_reminder(row)
            for row in rows
        ]

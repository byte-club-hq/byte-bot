from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class UserRecord:
    user_id: int
    discord_username: str
    leetcode_username: str | None = None

@dataclass
class ReminderChannel:
    id: int
    name: str

@dataclass
class Reminder:
    id: int
    event_id: int
    event_name: str
    reminder_minutes: int
    event_start: int

class DatabaseService:
    def __init__(self, database_path: str):
        self.database_path = database_path
        # sqlite treats values like "file:..." as connection URIs, not plain file paths.
        self._is_uri = database_path.startswith("file:")
        self.initialize()

    def _create_connection(self) -> sqlite3.Connection:
        # ":memory:" tells sqlite to keep everything in RAM for this connection only,
        # so there is no parent directory or database file to create on disk.
        if not self._is_uri and self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(self.database_path, uri=self._is_uri)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def get_connection(self):
        connection = self._create_connection()
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        # Safe to call on every startup; this only creates the table if it's missing.
        with self.get_connection() as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        discord_username TEXT NOT NULL,
                        leetcode_username TEXT
                    )
                    """
                )

                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS role_toggle_panels (
                        guild_id INTEGER NOT NULL,
                        message_id INTEGER,
                        role_id INTEGER,
                        role_name TEXT NOT NULL,
                        emoji TEXT NOT NULL,
                        title TEXT NOT NULL,
                        PRIMARY KEY (guild_id, role_name)
                    )
                    """
                )

                connection.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_role_toggle_panels_message
                    ON role_toggle_panels (guild_id, message_id, emoji)
                    """
                )

                # Create if not exists reminder channel
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reminder_channels (
                        channel_id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL
                    )
                    """
                )

                # Create if not exists reminders
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id INTEGER NOT NULL,
                        event_name TEXT NOT NULL,
                        text TEXT,
                        reminder_channel_id INTEGER NOT NULL,
                        reminder_minutes INTEGER,
                        event_start INTEGER NOT NULL,
                        sent_at INTEGER
                    )
                    """
                )

    def upsert_user(
        self,
        *,
        user_id: int | None = None,
        discord_username: str,
        leetcode_username: str | None = None,
    ) -> UserRecord:
        """Insert/update user - SQLite assigns the primary key for new users. Pass a user_id only when updating an existing user."""
        with self.get_connection() as connection:
            with connection:
                if user_id is None:
                    cursor = connection.execute(
                        """
                        INSERT INTO users (discord_username, leetcode_username)
                        VALUES (?, ?)
                        """,
                        (discord_username, leetcode_username),
                    )
                    user_id = cursor.lastrowid
                else:
                    connection.execute(
                        """
                        INSERT INTO users (user_id, discord_username, leetcode_username)
                        VALUES (?, ?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET
                            discord_username = excluded.discord_username,
                            leetcode_username = excluded.leetcode_username
                        """,
                        (user_id, discord_username, leetcode_username),
                    )

        return self.get_user(user_id)

    def get_user(self, user_id: int) -> UserRecord | None:
        with self.get_connection() as connection:
            row = connection.execute(
                """
                SELECT user_id, discord_username, leetcode_username
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        if row is None:
            return None

        return UserRecord(
            user_id=row["user_id"],
            discord_username=row["discord_username"],
            leetcode_username=row["leetcode_username"],
        )

    def get_reminder_channels(self) -> list[ReminderChannel]:
        channels = []
        with self.get_connection() as connection:
            rows = connection.execute(
                "SELECT channel_id, name FROM reminder_channels"
            ).fetchall()

            if not rows:
                return channels
            print('rows')
            print(rows)
            for row in rows:
                channels.append(ReminderChannel(
                    id=row[0],
                    name=row[1]
                ))
        return channels

    def set_channel_reminder(self, id, name) -> ReminderChannel:
        with self.get_connection() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO reminder_channels (channel_id, name)
                    VALUES (?, ?)
                    ON CONFLICT(channel_id) DO UPDATE SET name = excluded.name
                    """,
                    (id, name),
                )

        return ReminderChannel(
            id=id,
            name=name,
        )

    def remove_channel_reminder(self, id, name) -> bool:
            with self.get_connection() as connection:
                with connection:
                    cursor = connection.execute(
                        """
                        DELETE FROM reminder_channels
                        WHERE channel_id = ?
                        """,
                        (id,),
                    )
    
            return cursor.rowcount > 0

    def get_reminders(self) -> list[Reminder]:
        reminders = []
        with self.get_connection() as connection:
            rows = connection.execute(
                "SELECT id, event_id, event_name, reminder_minutes, event_start FROM reminders"
            ).fetchall()

            if not rows:
                return reminders
            print('rows')
            print(rows)
            for row in rows:
                reminders.append(Reminder(
                    id=row[0],
                    event_id=row[1],
                    event_name=row[2],
                    reminder_minutes=row[3],
                    event_start=row[4]
                ))

        return reminders

    def create_reminder(self, event_id: int, event_name: str, reminder_minutes: int, event_start: int):
        with self.get_connection() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO reminders (
                        event_id,
                        event_name,
                        text,
                        reminder_channel_id,
                        reminder_minutes,
                        event_start
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        event_id,
                        event_name,
                        text,
                        reminder_channel_id,
                        reminder_minutes,
                        event_start,
                    )
                )

#  CREATE TABLE IF NOT EXISTS reminders (
#                         id INTEGER PRIMARY KEY AUTOINCREMENT,
#                         event_id INTEGER,
#                         event_name TEXT,
#                         reminder_minutes INTEGER,
#                         event_start INTEGER NOT NULL
#                     )
# import sqlite3
# import logging

# # Configuración básica de logs (puedes usar el de tu app)6
# logger = logging.getLogger(__name__)

# def remove_channel_reminder(self, id) -> bool:
#     try:
#         with self.get_connection() as connection:
#             with connection:  # Si hay error aquí, hace ROLLBACK automáticamente
#                 cursor = connection.execute(reminder_channel_id
#                     """
#                     DELETE FROM reminder_channels
#                     WHERE channel_id = ?
#                     """,
#                     (id,),
#                 )
#                 return cursor.rowcount > 0

#     except sqlite3.Error as e:
#         # Captura errores como: base de datos bloqueada, archivo corrupto, etc.
#         logger.error(f"Error de SQLite al eliminar el canal {id}: {e}")
#         return False  # Devolvemos False porque la operación no tuvo éxito

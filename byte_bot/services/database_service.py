from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class UserRecord:
    user_id: int
    discord_username: str
    leetcode_username: str | None = None


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

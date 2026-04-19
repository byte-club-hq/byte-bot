from contextlib import closing, contextmanager
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

    def get_connection(self):
        return self._create_connection()

    @contextmanager
    def transaction(self, connection: sqlite3.Connection):
        with connection:
            yield connection

    def initialize(self) -> None:
        # Safe to call on every startup; this only creates the table if it's missing.
        with closing(self.get_connection()) as connection:
            with self.transaction(connection):
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        discord_username TEXT NOT NULL,
                        leetcode_username TEXT
                    )
                    """
                )

    def upsert_user(
        self,
        *,
        user_id: int,
        discord_username: str,
        leetcode_username: str | None = None,
    ) -> UserRecord:
        # Insert the user the first time we see them, otherwise refresh the stored names.
        with closing(self.get_connection()) as connection:
            with self.transaction(connection):
                cursor = connection.execute(
                    """
                    INSERT INTO users (user_id, discord_username, leetcode_username)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        discord_username = excluded.discord_username,
                        leetcode_username = excluded.leetcode_username
                    """,
                    (user_id, discord_username, leetcode_username),
                )

                if cursor.rowcount == 0:
                    raise ValueError(f"Failed to upsert user with id {user_id}")

        return self.get_user(user_id)

    def get_user(self, user_id: int) -> UserRecord | None:
        # Return None when the user has not been stored yet so callers can branch on that cleanly.
        with closing(self.get_connection()) as connection:
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


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

                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS youtube_tracker_state (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        uploads_playlist_id TEXT,
                        last_video_id TEXT,
                        last_published_at TEXT,
                        quota_date TEXT,
                        estimated_quota_used INTEGER NOT NULL DEFAULT 0,
                        quota_paused_until TEXT
                    )
                    """
                )

                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS youtube_processed_videos (
                        video_id TEXT PRIMARY KEY,
                        published_at TEXT NOT NULL,
                        processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                connection.execute(
                    """
                    INSERT OR IGNORE INTO youtube_tracker_state (id)
                    VALUES (1)
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

    def get_youtube_tracker_state(self) -> sqlite3.Row:
        with self.get_connection() as connection:
            return connection.execute(
                """
                SELECT uploads_playlist_id, last_video_id, last_published_at,
                       quota_date, estimated_quota_used, quota_paused_until
                FROM youtube_tracker_state
                WHERE id = 1
                """
            ).fetchone()

    def update_youtube_tracker_state(
        self,
        *,
        uploads_playlist_id: str | None = None,
        last_video_id: str | None = None,
        last_published_at: str | None = None,
        quota_date: str | None = None,
        estimated_quota_used: int | None = None,
        quota_paused_until: str | None = None,
        update_quota_paused_until: bool = False,
    ) -> None:
        with self.get_connection() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE youtube_tracker_state
                    SET uploads_playlist_id = COALESCE(?, uploads_playlist_id),
                        last_video_id = COALESCE(?, last_video_id),
                        last_published_at = COALESCE(?, last_published_at),
                        quota_date = COALESCE(?, quota_date),
                        estimated_quota_used = COALESCE(?, estimated_quota_used),
                        quota_paused_until = CASE WHEN ? THEN ? ELSE quota_paused_until END
                    WHERE id = 1
                    """,
                    (
                        uploads_playlist_id,
                        last_video_id,
                        last_published_at,
                        quota_date,
                        estimated_quota_used,
                        update_quota_paused_until,
                        quota_paused_until,
                    ),
                )

    def reset_youtube_quota_if_needed(self, quota_date: str) -> None:
        state = self.get_youtube_tracker_state()
        if state["quota_date"] == quota_date:
            return

        self.update_youtube_tracker_state(
            quota_date=quota_date,
            estimated_quota_used=0,
            quota_paused_until=None,
            update_quota_paused_until=True,
        )

    def increment_youtube_quota(self, quota_date: str, units: int = 1) -> int:
        self.reset_youtube_quota_if_needed(quota_date)
        with self.get_connection() as connection:
            with connection:
                connection.execute(
                    """
                    UPDATE youtube_tracker_state
                    SET estimated_quota_used = estimated_quota_used + ?
                    WHERE id = 1
                    """,
                    (units,),
                )
                row = connection.execute(
                    """
                    SELECT estimated_quota_used
                    FROM youtube_tracker_state
                    WHERE id = 1
                    """
                ).fetchone()

        return row["estimated_quota_used"]

    def get_youtube_processed_video_ids(self) -> set[str]:
        with self.get_connection() as connection:
            rows = connection.execute("SELECT video_id FROM youtube_processed_videos").fetchall()

        return {row["video_id"] for row in rows}

    def mark_youtube_video_processed(self, video_id: str, published_at: str) -> None:
        with self.get_connection() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO youtube_processed_videos (video_id, published_at)
                    VALUES (?, ?)
                    """,
                    (video_id, published_at),
                )

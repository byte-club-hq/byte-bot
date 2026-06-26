import sqlite3

import pytest

from byte_bot.services.database_service import DatabaseService


def test_database_service_initializes_users_table(database_path):
    database_service = DatabaseService(database_path)

    with database_service.get_connection() as connection:
        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'users'
            """
        ).fetchone()

    assert table["name"] == "users"


def test_database_service_initializes_role_toggle_role_id_column(database_path):
    database_service = DatabaseService(database_path)

    with database_service.get_connection() as connection:
        columns = connection.execute("PRAGMA table_info(role_toggle_panels)").fetchall()

    assert "role_id" in {column["name"] for column in columns}


def test_database_service_initializes_youtube_tracker_tables(database_path):
    database_service = DatabaseService(database_path)

    with database_service.get_connection() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    assert "youtube_tracker_state" in tables
    assert "youtube_processed_videos" in tables


def test_database_service_updates_youtube_tracker_state(database_path):
    database_service = DatabaseService(database_path)

    database_service.update_youtube_tracker_state(
        uploads_playlist_id="UU123",
        last_video_id="abc123",
        last_published_at="2026-06-25T00:00:00Z",
    )
    state = database_service.get_youtube_tracker_state()

    assert state["uploads_playlist_id"] == "UU123"
    assert state["last_video_id"] == "abc123"
    assert state["last_published_at"] == "2026-06-25T00:00:00Z"


def test_database_service_upserts_and_reads_user(database_path):
    database_service = DatabaseService(database_path)

    user = database_service.upsert_user(
        discord_username="byte-user",
        leetcode_username="two-sum",
    )

    stored_user = database_service.get_user(user.user_id)

    assert user == stored_user
    assert stored_user.user_id == 1
    assert stored_user.discord_username == "byte-user"
    assert stored_user.leetcode_username == "two-sum"


def test_database_service_updates_existing_user(database_path):
    database_service = DatabaseService(database_path)
    original_user = database_service.upsert_user(
        discord_username="old-name",
        leetcode_username="old-lc",
    )

    updated_user = database_service.upsert_user(
        user_id=original_user.user_id,
        discord_username="new-name",
        leetcode_username="new-lc",
    )

    assert updated_user.discord_username == "new-name"
    assert updated_user.leetcode_username == "new-lc"


def test_database_service_creates_database_file_when_missing(tmp_path):
    database_file = tmp_path / "data" / "byte_bot.db"

    DatabaseService(str(database_file))

    assert database_file.exists()


def test_database_service_reuses_connection_across_transactions(database_path):
    database_service = DatabaseService(database_path)

    with database_service.get_connection() as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO users (user_id, discord_username, leetcode_username)
                VALUES (?, ?, ?)
                """,
                (1, "first-user", "first-lc"),
            )

        with connection:
            connection.execute(
                """
                UPDATE users
                SET discord_username = ?
                WHERE user_id = ?
                """,
                ("updated-user", 1),
            )

    stored_user = database_service.get_user(1)

    assert stored_user.discord_username == "updated-user"


def test_database_service_returns_none_for_unknown_user(database_path):
    database_service = DatabaseService(database_path)

    assert database_service.get_user(999) is None


def test_database_service_upsert_allows_none_leetcode_username(database_path):
    database_service = DatabaseService(database_path)

    stored_user = database_service.upsert_user(
        discord_username="byte-user",
        leetcode_username=None,
    )

    assert stored_user.leetcode_username is None


def test_database_service_upsert_noop_returns_existing_user(database_path):
    database_service = DatabaseService(database_path)
    original_user = database_service.upsert_user(
        discord_username="byte-user",
        leetcode_username="two-sum",
    )

    stored_user = database_service.upsert_user(
        user_id=original_user.user_id,
        discord_username="byte-user",
        leetcode_username="two-sum",
    )

    assert stored_user == original_user


def test_database_service_rolls_back_failed_transaction(database_path):
    database_service = DatabaseService(database_path)

    with pytest.raises(sqlite3.IntegrityError):
        with database_service.get_connection() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO users (user_id, discord_username, leetcode_username)
                    VALUES (?, ?, ?)
                    """,
                    (1, "first-user", "first-lc"),
                )
                connection.execute(
                    """
                    INSERT INTO users (user_id, discord_username, leetcode_username)
                    VALUES (?, ?, ?)
                    """,
                    (1, "duplicate-user", "duplicate-lc"),
                )

    assert database_service.get_user(1) is None

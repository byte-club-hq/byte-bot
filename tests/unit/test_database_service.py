from contextlib import closing

from byte_bot.services.database_service import DatabaseService


def test_database_service_initializes_users_table(database_path):
    database_service = DatabaseService(database_path)

    with closing(database_service.get_connection()) as connection:
        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'users'
            """
        ).fetchone()

    assert table["name"] == "users"


def test_database_service_upserts_and_reads_user(database_path):
    database_service = DatabaseService(database_path)

    user = database_service.upsert_user(
        user_id=123,
        discord_username="byte-user",
        leetcode_username="two-sum",
    )

    stored_user = database_service.get_user(123)

    assert user == stored_user
    assert stored_user.user_id == 123
    assert stored_user.discord_username == "byte-user"
    assert stored_user.leetcode_username == "two-sum"


def test_database_service_updates_existing_user(database_path):
    database_service = DatabaseService(database_path)
    database_service.upsert_user(
        user_id=123,
        discord_username="old-name",
        leetcode_username="old-lc",
    )

    updated_user = database_service.upsert_user(
        user_id=123,
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

    with closing(database_service.get_connection()) as connection:
        with database_service.transaction(connection):
            connection.execute(
                """
                INSERT INTO users (user_id, discord_username, leetcode_username)
                VALUES (?, ?, ?)
                """,
                (1, "first-user", "first-lc"),
            )

        with database_service.transaction(connection):
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

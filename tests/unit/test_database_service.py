from byte_bot.services.database_service import DatabaseService


def test_database_service_initializes_users_table(database_path):
    database_service = DatabaseService(database_path)

    table = database_service.connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = 'users'
        """
    ).fetchone()

    assert table["name"] == "users"

    database_service.close()


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

    database_service.close()


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

    database_service.close()


def test_database_service_creates_database_file_when_missing(tmp_path):
    database_file = tmp_path / "data" / "byte_bot.db"

    database_service = DatabaseService(str(database_file))

    assert database_file.exists()

    database_service.close()

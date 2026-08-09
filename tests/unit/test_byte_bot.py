from byte_bot.byte_bot import ByteBot
from byte_bot.byte_bot import health_check


class BotConfig:
    FEATURE_FORUM_CHANNEL_ID = 1234567890


def test_health_check_returns_ok_status():
    result = health_check()
    assert result == {"status": "ok", "service": "byte_bot"}


def test_byte_bot_initializes_database_service(tmp_path):
    original_database_path = ByteBot.DATABASE_PATH
    ByteBot.DATABASE_PATH = tmp_path / "byte_bot.db"
    bot = ByteBot(BotConfig())

    try:
        with bot.database_service.get_connection() as connection:
            table = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = 'users'
                """
            ).fetchone()
    finally:
        ByteBot.DATABASE_PATH = original_database_path

    assert table["name"] == "users"

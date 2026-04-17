from byte_bot.byte_bot import health_check
from byte_bot.byte_bot import ByteBot

class TestConfig:
    FEATURE_FORUM_CHANNEL_ID = 1234567890
    DATABASE_PATH = ":memory:"

def test_health_check_returns_ok_status():
    result = health_check()
    assert result == {"status": "ok", "service": "byte_bot"}

def test_byte_bot_initializes_database_service():
    bot = ByteBot(TestConfig())

    try:
        with bot.database_service.get_connection() as connection:
            table = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = 'users'
                """
            ).fetchone()

        assert table["name"] == "users"
    finally:
        bot.database_service.close()

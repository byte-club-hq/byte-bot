from contextlib import closing

from byte_bot.byte_bot import ByteBot
from byte_bot.byte_bot import health_check


class BotConfig:
    FEATURE_FORUM_CHANNEL_ID = 1234567890

    def __init__(self, database_path: str):
        self.DATABASE_PATH = database_path


def test_health_check_returns_ok_status():
    result = health_check()
    assert result == {"status": "ok", "service": "byte_bot"}


def test_byte_bot_initializes_database_service(tmp_path):
    bot = ByteBot(BotConfig(str(tmp_path / "byte_bot.db")))

    with closing(bot.database_service.get_connection()) as connection:
        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'users'
            """
        ).fetchone()

    assert table["name"] == "users"

import logging

from byte_bot.byte_bot import ByteBot
from byte_bot.config import Config

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def main():
    if not (token := Config.DISCORD_TOKEN):  # Ensure the token is set before proceeding
        raise ValueError("DISCORD_TOKEN environment variable is not set.")
    if not Config.FEATURE_FORUM_CHANNEL_ID:
        raise ValueError("FEATURE_FORUM_CHANNEL_ID environment variable is not set.")
    bot = ByteBot(feature_forum_channel_id=Config.FEATURE_FORUM_CHANNEL_ID)
    bot.run(token)


# Entry point for the application
if __name__ == "__main__":
    try:
        log.debug("Starting byte-bot...")
        main()
    except Exception as e:
        log.exception(e)
        exit(1)  # Ensure we exit with a non-zero code on failure
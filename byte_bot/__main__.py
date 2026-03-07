import logging
from os import environ

from dotenv import load_dotenv

from byte_bot.byte_bot import ByteBot

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def main():
    required_env_vars = [
        "DISCORD_TOKEN",
        "FEATURE_FORUM_CHANNEL_ID"
    ]
    if missing_tokens:= [var for var in required_env_vars if not environ.get(var)]: # Ensure the token is set before proceeding
        raise ValueError(f"Missing environment variables: {', '.join(missing_tokens)}")
    bot = ByteBot(
        feature_forum_channel_id=int(environ["FEATURE_FORUM_CHANNEL_ID"])
    )
    bot.run(environ["DISCORD_TOKEN"])


# Entry point for the application
if __name__ == "__main__":
    load_dotenv()

    try:
        log.debug("Starting byte-bot...")
        main()
    except Exception as e:
        log.exception(e)
        exit(1)  # Ensure we exit with a non-zero code on failure

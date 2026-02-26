import logging
from os import environ

from dotenv import load_dotenv

from byte_bot.byte_bot import ByteBot

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def main():
    if not (token := environ.get("DISCORD_TOKEN")):  # Ensure the token is set before proceeding
        raise ValueError("DISCORD_TOKEN environment variable is not set.")
    bot = ByteBot()
    bot.run(token)


# Entry point for the application
if __name__ == "__main__":
    load_dotenv()

    try:
        log.debug("Starting byte-bot...")
        main()
    except Exception as e:
        log.exception(e)
        exit(1)  # Ensure we exit with a non-zero code on failure

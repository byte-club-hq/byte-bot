import logging
import os

from dotenv import load_dotenv

from byte_bot.byte_bot import ByteBot
from byte_bot.config import Config

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

def get_config() -> Config:
    discord_token = os.environ.get("DISCORD_TOKEN")
    forum_channel_id_str = os.environ.get("FEATURE_FORUM_CHANNEL_ID")

    if not discord_token:  # Ensure the token is set before proceeding
        raise ValueError("DISCORD_TOKEN environment variable is not set.")
    if not forum_channel_id_str: 
        raise ValueError("FEATURE_FORUM_CHANNEL_ID environment variable is not set.")
    
    try:
        forum_channel_id = int(forum_channel_id_str)
    except ValueError:
        raise ValueError("FEATURE_FORUM_CHANNEL_ID must be an integer.")
    
    return Config(DISCORD_TOKEN=discord_token, FEATURE_FORUM_CHANNEL_ID=forum_channel_id)

def main():
    config = get_config()
    bot = ByteBot(config)
    bot.run(config.DISCORD_TOKEN)


# Entry point for the application
if __name__ == "__main__":
    load_dotenv()
    
    try:
        log.debug("Starting byte-bot...")
        main()
    except Exception as e:
        log.exception(e)
        exit(1)  # Ensure we exit with a non-zero code on failure
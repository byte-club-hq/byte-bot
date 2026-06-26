import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from byte_bot.byte_bot import ByteBot
from byte_bot.config import Config

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

def get_config() -> Config:
    discord_token = os.environ.get("DISCORD_TOKEN")
    forum_channel_id_str = os.environ.get("FEATURE_FORUM_CHANNEL_ID")

    # Keep a local sqlite file by default so the bot can start without extra setup.
    database_path = os.environ.get("DATABASE_PATH") or str(
        Path(__file__).resolve().parents[1] / "database" / "byte_bot.db"
    )

    role_channel_id_str = os.environ.get("ROLE_CHANNEL_ID")
    social_tracker_channel_id_str = os.environ.get("SOCIAL_TRACKER_CHANNEL_ID")
    youtube_channel_id = os.environ.get("YOUTUBE_CHANNEL_ID")
    youtube_api_key = os.environ.get("YOUTUBE_API_KEY")
    tiktok_username = os.environ.get("TIKTOK_USERNAME")
    interval_str = os.environ.get("INTERVAL")

    if not discord_token:  # Ensure the token is set before proceeding
        raise ValueError("DISCORD_TOKEN environment variable is not set.")
    if not forum_channel_id_str:
        raise ValueError("FEATURE_FORUM_CHANNEL_ID environment variable is not set.")

    try:
        forum_channel_id = int(forum_channel_id_str)
    except ValueError:
        raise ValueError("FEATURE_FORUM_CHANNEL_ID must be an integer.")

    role_channel_id = None
    if role_channel_id_str:
        try:
            role_channel_id = int(role_channel_id_str)
        except ValueError:
            raise ValueError("ROLE_CHANNEL_ID must be an integer.")

    social_tracker_channel_id = None
    if social_tracker_channel_id_str:
        try:
            social_tracker_channel_id = int(social_tracker_channel_id_str)
        except ValueError:
            raise ValueError("SOCIAL_TRACKER_CHANNEL_ID must be an integer.")

    interval = 900
    if interval_str:
        try:
            interval = int(interval_str)
        except ValueError:
            raise ValueError("INTERVAL must be an integer number of seconds.")
        if interval < 300:
            raise ValueError("INTERVAL must be at least 300 seconds.")

    return Config(
        DISCORD_TOKEN=discord_token,
        FEATURE_FORUM_CHANNEL_ID=forum_channel_id,
        DATABASE_PATH=database_path,
        ROLE_CHANNEL_ID=role_channel_id,
        SOCIAL_TRACKER_CHANNEL_ID=social_tracker_channel_id,
        YOUTUBE_CHANNEL_ID=youtube_channel_id,
        YOUTUBE_API_KEY=youtube_api_key,
        TIKTOK_USERNAME=tiktok_username,
        INTERVAL=interval,
    )

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

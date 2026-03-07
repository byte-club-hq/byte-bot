import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
    FEATURE_FORUM_CHANNEL_ID = int(os.environ["FEATURE_FORUM_CHANNEL_ID"]) if os.environ.get("FEATURE_FORUM_CHANNEL_ID") else None
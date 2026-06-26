from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    DISCORD_TOKEN: str
    FEATURE_FORUM_CHANNEL_ID: int
    DATABASE_PATH: str
    ROLE_CHANNEL_ID: Optional[int] = None
    SOCIAL_TRACKER_CHANNEL_ID: Optional[int] = None
    YOUTUBE_CHANNEL_ID: Optional[str] = None
    YOUTUBE_API_KEY: Optional[str] = None
    TIKTOK_USERNAME: Optional[str] = None
    INTERVAL: int = 900

from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    DISCORD_TOKEN: str
    FEATURE_FORUM_CHANNEL_ID: int
    DATABASE_PATH: str
    ROLE_CHANNEL_ID: Optional[int] = None

from dataclasses import dataclass

@dataclass
class Config:
    DISCORD_TOKEN: str
    FEATURE_FORUM_CHANNEL_ID: int
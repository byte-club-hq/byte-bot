from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FeatureSuggestion:
    title: str
    summary: str
    image: Optional[str] = None

    def __post_init__(self):
        if len(self.title) > 256:
            raise ValueError("The title cannot exceed 256 characters.")
        if len(self.summary) > 1024:
            raise ValueError("The summary cannot exceed 1024 characters.")
        if self.image is not None: 
            if not self.image.startswith("https://"):
                raise ValueError("Image URL must be a direct link starting with https://")


def create_feature_suggestion(title: str, summary: str, image: Optional[str] = None) -> FeatureSuggestion:
    return FeatureSuggestion(title=title, summary=summary, image=image)

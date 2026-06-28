from dataclasses import dataclass, field
from typing import Final


@dataclass
class FeatureSuggestion:
    title: str
    summary: str
    image: str | None = None
    summary_chunked: list[str] = field(init=False, repr=False, default_factory=list)

    def __post_init__(self):
        if len(self.title) > 256:
            raise ValueError("The title cannot exceed 256 characters.")
        if self.image is not None: 
            if not self.image.startswith(("http://", "https://")):
                raise ValueError("Image URL must be a direct link starting with http:// or https://")
        self._chunk_text()

    def _chunk_text(self) -> None:
        field_text_max: Final[int] = 1024
        if len(self.summary) <= field_text_max: # Early return for a short enough message
            self.summary_chunked = [self.summary]
            return
        
        words: list[str] = self.summary.split()
        chunks: list[str] = []
        current: str = words[0]

        for w in words[1:]:
            if len(current) + 1 + len(w) <= field_text_max: # +1 for the space
                current = current + " " + w
            else:
                chunks.append(current)
                current = w
        chunks.append(current)

        self.summary_chunked = chunks


def create_feature_suggestion(title: str, summary: str, image: str | None = None) -> FeatureSuggestion:
    return FeatureSuggestion(title=title, summary=summary, image=image)

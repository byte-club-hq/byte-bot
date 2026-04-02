from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSuggestion:
    title: str
    summary: str

    def __post_init__(self):
        if len(self.title) > 256:
            raise ValueError("The title cannot exceed 256 characters.")
        if len(self.summary) > 1024:
            raise ValueError("The summary cannot exceed 1024 characters.")


def create_feature_suggestion(title: str, summary: str) -> FeatureSuggestion:
    return FeatureSuggestion(title=title, summary=summary)

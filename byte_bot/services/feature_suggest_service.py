from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSuggestion:
    title: str
    summary: str


def create_feature_suggestion(title: str, summary: str) -> FeatureSuggestion:
    if len(title) > 256:
        raise ValueError("The title cannot exceed 256 characters.")
    if len(summary) > 1024:
        raise ValueError("The summary cannot exceed 1024 characters.")

    return FeatureSuggestion(title=title, summary=summary)

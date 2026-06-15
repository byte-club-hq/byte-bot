import pytest

from byte_bot.services.feature_suggest_service import create_feature_suggestion


def test_create_feature_suggestion_returns_dataclass_for_valid_input():
    result = create_feature_suggestion("Dark Mode", "Add a dark theme for users.")

    assert result.title == "Dark Mode"
    assert result.summary == "Add a dark theme for users."


def test_create_feature_suggestion_allows_max_title_length():
    result = create_feature_suggestion("A" * 256, "Short summary")

    assert result.title == "A" * 256


def test_create_feature_suggestion_raises_for_title_too_long():
    with pytest.raises(ValueError, match="The title cannot exceed 256 characters."):
        create_feature_suggestion("A" * 257, "Short summary")


def test_create_feature_suggestion_allows_max_summary_length():
    result = create_feature_suggestion("Dark Mode", "B" * 1024)

    assert result.summary == "B" * 1024


def test_create_feature_suggestion_raises_for_summary_too_long():
    with pytest.raises(ValueError, match="The summary cannot exceed 1024 characters."):
        create_feature_suggestion("Dark Mode", "B" * 1025)

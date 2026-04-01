import pytest

import byte_bot.services.leetcode_service as leetcode


class MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_get_leetcode_profile_returns_parsed_user(monkeypatch):
    def fake_post(url, json):
        return MockResponse(
            {
                "data": {
                    "matchedUser": {
                        "username": "niits",
                        "profile": {
                            "realName": "Niits Test",
                            "ranking": 12345,
                            "reputation": 10,
                            "countryName": "Morocco",
                        },
                        "submitStats": {
                            "acSubmissionNum": [
                                {"difficulty": "Easy", "count": 50},
                                {"difficulty": "Medium", "count": 40},
                            ]
                        },
                    }
                }
            }
        )

    monkeypatch.setattr(leetcode.requests, "post", fake_post)

    result = leetcode.get_leetcode_profile("niits")

    assert result.username == "niits"
    assert result.profile.real_name == "Niits Test"
    assert result.profile.ranking == 12345
    assert result.profile.reputation == 10
    assert result.profile.country == "Morocco"
    assert len(result.submissions) == 2
    assert result.submissions[0].difficulty == "Easy"
    assert result.submissions[0].count == 50


def test_get_leetcode_profile_raises_for_unknown_username(monkeypatch):
    def fake_post(url, json):
        return MockResponse({"data": {"matchedUser": None}})

    monkeypatch.setattr(leetcode.requests, "post", fake_post)

    with pytest.raises(ValueError, match="Failed to find a leetcode user with that username"):
        leetcode.get_leetcode_profile("unknownuser")


def test_get_leetcode_daily_returns_problem(monkeypatch):
    def fake_post(url, json):
        return MockResponse(
            {
                "data": {
                    "activeDailyCodingChallengeQuestion": {
                        "date": "1111-11-11",
                        "link": "/problems/test-title",
                        "question": {
                            "title": "testTitle",
                            "titleSlug": "test-title",
                            "difficulty": "Easy",
                            "acRate": 1234,
                            "questionFrontendId": "1234",
                        },
                    }
                }
            }
        )

    monkeypatch.setattr(leetcode.requests, "post", fake_post)

    result = leetcode.get_leetcode_daily()

    assert result["link"] == "/problems/test-title"
    assert result["question"]["title"] == "testTitle"
    assert result["question"]["difficulty"] == "Easy"


def test_get_leetcode_daily_raises_when_problem_missing(monkeypatch):
    def fake_post(url, json):
        return MockResponse({"data": {"activeDailyCodingChallengeQuestion": None}})

    monkeypatch.setattr(leetcode.requests, "post", fake_post)

    with pytest.raises(ValueError, match="Failed to find a daily leetcode problem"):
        leetcode.get_leetcode_daily()


def test_get_leetcode_random_returns_filtered_problem(monkeypatch):
    def fake_get(url):
        return MockResponse(
            {
                "stat_status_pairs": [
                    {
                        "stat": {
                            "question__title": "Wrong Difficulty",
                            "question__title_slug": "wrong-difficulty",
                        },
                        "difficulty": {"level": 2},
                    },
                    {
                        "stat": {
                            "question__title": "Two Sum",
                            "question__title_slug": "two-sum",
                        },
                        "difficulty": {"level": 1},
                    },
                ]
            }
        )

    monkeypatch.setattr(leetcode.requests, "get", fake_get)
    monkeypatch.setattr(leetcode.random, "choice", lambda sequence: sequence[0])

    result = leetcode.get_leetcode_random("Easy")

    assert result["stat"]["question__title"] == "Two Sum"
    assert result["stat"]["question__title_slug"] == "two-sum"


def test_get_leetcode_random_raises_when_difficulty_missing():
    with pytest.raises(ValueError, match="You must provide a difficulty"):
        leetcode.get_leetcode_random(None)


def test_get_leetcode_random_raises_when_difficulty_invalid():
    with pytest.raises(ValueError, match="You must provide a difficulty"):
        leetcode.get_leetcode_random("Impossible")

import pytest
import discord.ext.test as dpytest

import byte_bot.cogs.leetcode as leetcode_module

class MockResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

def fake_post(url, json):
    username = json["variables"]["username"]

    if username == "niits":
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
                                {"difficulty": "All", "count": 100},
                                {"difficulty": "Easy", "count": 50},
                                {"difficulty": "Medium", "count": 40},
                                {"difficulty": "Hard", "count": 10},
                            ]
                        },
                    }
                }
            }
        )

    return MockResponse({"data": {"matchedUser": None}})

@pytest.mark.asyncio
async def test_leetcode_no_username(bot):
    await dpytest.message("+leetcode")
    assert dpytest.verify().message().contains().content("You must provide a leetcode username")

@pytest.mark.asyncio
async def test_leetcode_username(bot, monkeypatch):
    monkeypatch.setattr(leetcode_module.requests, "post", fake_post)
    await dpytest.message("+leetcode niits")
    resp = dpytest.get_message()
    assert len(resp.embeds) == 1

@pytest.mark.asyncio
async def test_leetcode_unknown_username(bot, monkeypatch):
    monkeypatch.setattr(leetcode_module.requests, "post", fake_post)
    await dpytest.message("+leetcode unknownuser")
    assert dpytest.verify().message().contains().content("Failed to find a leetcode user with that username")


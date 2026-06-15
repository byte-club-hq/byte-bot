import pytest
import discord.ext.test as dpytest

from byte_bot.services.leetcode_service import LeetCodeUser, Profile, SubmissionStat


def patch_command_service(monkeypatch, command, service_name, replacement):
    monkeypatch.setitem(command.callback.__globals__, service_name, replacement)


@pytest.mark.asyncio
async def test_leetcode_no_username(bot):
    await dpytest.message("+leetcode_profile")
    assert dpytest.verify().message().contains().content("You must provide a leetcode username")


@pytest.mark.asyncio
async def test_leetcode_username(bot, monkeypatch):
    patch_command_service(
        monkeypatch,
        bot.get_command("leetcode_profile"),
        "get_leetcode_profile",
        lambda profile: LeetCodeUser(
            username="niits",
            profile=Profile(
                real_name="Niits Test",
                ranking=12345,
                reputation=10,
                country="Morocco",
            ),
            submissions=[
                SubmissionStat(difficulty="Easy", count=50),
                SubmissionStat(difficulty="Medium", count=40),
            ],
        ),
    )

    await dpytest.message("+leetcode_profile niits")
    resp = dpytest.get_message()
    assert len(resp.embeds) == 1


@pytest.mark.asyncio
async def test_leetcode_unknown_username(bot, monkeypatch):
    def raise_value_error(profile):
        raise ValueError("Failed to find a leetcode user with that username")

    patch_command_service(
        monkeypatch,
        bot.get_command("leetcode_profile"),
        "get_leetcode_profile",
        raise_value_error,
    )

    await dpytest.message("+leetcode_profile unknownuser")
    assert dpytest.verify().message().contains().content("Failed to find a leetcode user with that username")


@pytest.mark.asyncio
async def test_leetcode_daily(bot, monkeypatch):
    patch_command_service(
        monkeypatch,
        bot.get_command("leetcode_daily"),
        "get_leetcode_daily",
        lambda: {
            "link": "/problems/test-title",
            "question": {
                "title": "testTitle",
                "difficulty": "Easy",
            },
        },
    )

    await dpytest.message("+leetcode_daily")
    resp = dpytest.get_message()
    assert len(resp.embeds) == 1


@pytest.mark.asyncio
async def test_leetcode_random(bot, monkeypatch):
    patch_command_service(
        monkeypatch,
        bot.get_command("leetcode_random"),
        "get_leetcode_random",
        lambda difficulty: {
            "stat": {
                "question__title": "Two Sum",
                "question__title_slug": "two-sum",
            }
        },
    )

    await dpytest.message("+leetcode_random Easy")
    resp = dpytest.get_message()
    assert len(resp.embeds) == 1


@pytest.mark.asyncio
async def test_leetcode_random_no_input(bot, monkeypatch):
    await dpytest.message("+leetcode_random")
    assert dpytest.verify().message().contains().content("You must provide a difficulty")

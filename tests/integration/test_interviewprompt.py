import pytest
import discord.ext.test as dpytest


def _patch_interviewprompt_services(monkeypatch, bot, replacement):
    command = bot.get_command("interviewprompt")
    monkeypatch.setitem(command.callback.__globals__, "get_random_question", replacement)
    monkeypatch.setitem(
        command.callback.__globals__,
        "QUESTIONS",
        [
            {
                "question": "What is Python?",
                "answer": "A programming language.",
            }
        ],
    )


@pytest.mark.asyncio
async def test_interviewprompt_sends_embed(bot, monkeypatch):
    _patch_interviewprompt_services(
        monkeypatch,
        bot,
        lambda: {
            "question": "What is Python?",
            "answer": "A programming language.",
        },
    )

    await dpytest.message("+interviewprompt")
    msg = dpytest.get_message()

    assert len(msg.embeds) == 1
    assert msg.embeds[0].title == "Ready for an interview?"


@pytest.mark.asyncio
async def test_interviewprompt_embed_contains_question_and_hidden_answer(bot, monkeypatch):
    _patch_interviewprompt_services(
        monkeypatch,
        bot,
        lambda: {
            "question": "Explain list comprehensions.",
            "answer": "A compact syntax for building lists.",
        },
    )

    await dpytest.message("+interviewprompt")
    msg = dpytest.get_message()
    field_map = {field.name: field.value for field in msg.embeds[0].fields}

    assert field_map["Question:"] == "Explain list comprehensions."
    assert field_map["Answer"] == "||A compact syntax for building lists.||"


@pytest.mark.asyncio
async def test_interviewprompt_adds_quiz_source_button_to_view(bot, monkeypatch):
    added_items = []

    _patch_interviewprompt_services(
        monkeypatch,
        bot,
        lambda: {
            "question": "What is Python?",
            "answer": "A programming language.",
        },
    )
    command = bot.get_command("interviewprompt")
    interview_view_class = command.callback.__globals__["InterviewView"]
    original_add_item = interview_view_class.add_item

    def spy_add_item(self, item):
        added_items.append(item)
        return original_add_item(self, item)

    monkeypatch.setattr(interview_view_class, "add_item", spy_add_item)

    await dpytest.message("+interviewprompt")

    assert len(added_items) == 1
    assert added_items[0].label == "Quiz Source"

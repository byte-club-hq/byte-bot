import byte_bot.services.interviewprompt_service as interviewprompt


def test_get_random_question_returns_choice_from_questions(monkeypatch):
    monkeypatch.setattr(interviewprompt.random, "choice", lambda sequence: sequence[0])

    result = interviewprompt.get_random_question()

    assert result == interviewprompt.QUESTIONS[0]
    assert "question" in result
    assert "answer" in result

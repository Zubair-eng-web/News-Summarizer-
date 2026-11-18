from types import SimpleNamespace

from app.agents.research import NO_INFO, Doc, answer_question

DOCS = [
    Doc(
        "Bank of England lifts rate",
        "Bank of England lifts interest rate to fight inflation.",
        [("BBC", "http://bbc/1")],
        "story",
    ),
]


class FlakyModels:
    """Rewrite hamesha chalta hai. Jawab wali calls `answers` list ke hisaab se aati hain."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.answer_calls = 0

    def generate_content(self, **kwargs):
        if "search query" in kwargs["config"].system_instruction:
            return SimpleNamespace(text="interest rate inflation")
        self.answer_calls += 1
        text = self.answers.pop(0) if self.answers else ""
        return SimpleNamespace(text=text)


class FlakyClient:
    def __init__(self, answers):
        self.models = FlakyModels(answers)


def test_empty_reply_is_retried_once():
    client = FlakyClient(["", "Bank ne rate badhaya [1]."])
    result = answer_question("sawal", client=client, docs=DOCS)
    assert result["answer"] == "Bank ne rate badhaya [1]."
    assert client.models.answer_calls == 2


def test_persistent_empty_reply_stops_after_two_tries():
    client = FlakyClient([])
    result = answer_question("sawal", client=client, docs=DOCS)
    assert result["answer"] == NO_INFO
    assert result["sources"] == []
    assert client.models.answer_calls == 2

from types import SimpleNamespace

from app.agents.video_agent import parse_video_json, prepare_transcript, summarize_video
from app.core.video import Video

VIDEO = Video("abc123DEF45", "Big news", "https://youtu.be/abc123DEF45", "BBC News", None, "A description.")
GOOD = '{"summary": "Short summary.", "key_points": ["One", "Two", ""], "takeaway": "Main idea."}'


class FakeModels:
    def __init__(self, text):
        self.text = text
        self.last = ""

    def generate_content(self, **kwargs):
        self.last = kwargs["contents"]
        return SimpleNamespace(text=self.text)


class FakeClient:
    def __init__(self, text):
        self.models = FakeModels(text)


def test_prepare_transcript_short_text_is_only_cleaned():
    assert prepare_transcript("a  b\n c") == "a b c"


def test_prepare_transcript_long_keeps_head_and_tail():
    text = "H" * 100 + "m" * 50000 + "T" * 100
    result = prepare_transcript(text, max_chars=1000)
    assert result.startswith("H" * 100)
    assert result.endswith("T" * 100)
    assert " ... " in result
    assert len(result) <= 1010


def test_parse_valid_and_fenced_json():
    expected = {"summary": "Short summary.", "key_points": ["One", "Two"], "takeaway": "Main idea."}
    assert parse_video_json(GOOD) == expected
    assert parse_video_json("```json\n" + GOOD + "\n```") == expected


def test_parse_invalid_json_returns_none():
    assert parse_video_json("not json") is None
    assert parse_video_json("[]") is None
    assert parse_video_json('{"summary": "", "key_points": []}') is None


def test_summarize_with_transcript():
    client = FakeClient(GOOD)
    result = summarize_video(VIDEO, "hello transcript text", client)
    assert result.has_transcript is True
    assert result.summary == "Short summary."
    assert result.key_points == ["One", "Two"]
    assert result.takeaway == "Main idea."
    assert result.video_id == "abc123DEF45"
    assert "hello transcript text" in client.models.last


def test_summarize_without_transcript_uses_description():
    client = FakeClient(GOOD)
    result = summarize_video(VIDEO, None, client)
    assert result.has_transcript is False
    assert "No transcript" in client.models.last
    assert "A description." in client.models.last


def test_summarize_bad_json_falls_back():
    result = summarize_video(VIDEO, "some transcript", FakeClient("garbage"))
    assert result.summary == "A description."
    assert result.key_points == []
    assert result.has_transcript is True

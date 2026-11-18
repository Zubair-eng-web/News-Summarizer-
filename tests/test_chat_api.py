import pytest
from fastapi.testclient import TestClient

from app.agents.research import ResearchError
from app.api import routes
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_returns_answer(client, monkeypatch):
    seen = []

    def fake(question):
        seen.append(question)
        return {"question": question, "query": "q", "answer": "Jawab [1]", "sources": []}

    monkeypatch.setattr(routes, "answer_question", fake)
    r = client.post("/chat", json={"question": "  Bank ne kya kiya?  "})
    assert r.status_code == 200
    assert r.json()["answer"] == "Jawab [1]"
    assert seen == ["Bank ne kya kiya?"]  # extra spaces hat gaye


def test_chat_empty_question_rejected(client):
    assert client.post("/chat", json={"question": ""}).status_code == 422


def test_chat_whitespace_question_rejected(client):
    assert client.post("/chat", json={"question": "   "}).status_code == 400


def test_chat_too_long_question_rejected(client):
    assert client.post("/chat", json={"question": "a" * 501}).status_code == 422


def test_chat_missing_api_key_gives_503(client, monkeypatch):
    def fake(question):
        raise ValueError("GEMINI_API_KEY .env file me set nahi hai")

    monkeypatch.setattr(routes, "answer_question", fake)
    assert client.post("/chat", json={"question": "hello"}).status_code == 503


def test_chat_research_error_gives_502(client, monkeypatch):
    def fake(question):
        raise ResearchError("Model ne khali jawab diya")

    monkeypatch.setattr(routes, "answer_question", fake)
    assert client.post("/chat", json={"question": "hello"}).status_code == 502

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes


def make_client(monkeypatch):
    monkeypatch.setattr(routes, "get_recent_stories", lambda **kw: [])
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def test_hours_has_an_upper_bound(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/stories?hours=99999999999").status_code == 422
    assert client.get("/stories?hours=0").status_code == 422
    assert client.get("/stories?hours=48").status_code == 200


def test_bad_priority_still_rejected(monkeypatch):
    client = make_client(monkeypatch)
    assert client.get("/stories?priority=urgent").status_code == 400

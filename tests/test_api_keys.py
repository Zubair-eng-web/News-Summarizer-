import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from google.genai import errors
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import keys as keys_api
from app.core import api_keys, models  # noqa: F401
from app.core.config import settings
from app.core.database import Base

GOOD = "AIza" + "x" * 35


@pytest.fixture
def factory(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    make = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(api_keys, "SessionLocal", make)
    monkeypatch.setattr(api_keys, "init_db", lambda: None)
    api_keys._exhausted.clear()
    return make


def test_add_list_remove_masks_the_key(factory):
    added = api_keys.add_key(GOOD)
    assert added["hint"] == "...xxxx"
    rows = api_keys.list_keys()
    assert len(rows) == 1 and GOOD not in str(rows)
    assert api_keys.remove_key(added["id"]) is True
    assert api_keys.remove_key(added["id"]) is False


def test_bad_and_duplicate_keys(factory):
    with pytest.raises(api_keys.ApiKeyInputError):
        api_keys.add_key("short")
    with pytest.raises(api_keys.ApiKeyInputError):
        api_keys.add_key("has space " + "x" * 30)
    api_keys.add_key(GOOD)
    with pytest.raises(api_keys.ApiKeyInputError):
        api_keys.add_key(GOOD)


def test_candidates_put_env_key_first_without_duplicates(factory, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", GOOD)
    api_keys.add_key(GOOD)
    api_keys.add_key("AIza" + "y" * 35)
    assert api_keys.candidate_keys() == [GOOD, "AIza" + "y" * 35]


class Quota(errors.APIError):
    def __init__(self):
        self.code = 429
        Exception.__init__(self, "quota")


class Broken(errors.APIError):
    def __init__(self):
        self.code = 500
        Exception.__init__(self, "server")


class FakeClient:
    behaviour: dict = {}

    def __init__(self, api_key):
        outer = self

        class Models:
            def generate_content(self, **kw):
                what = FakeClient.behaviour[api_key]
                if what is not None:
                    raise what
                return "ok:" + api_key

        outer.models = Models()


def test_rotating_client_switches_on_quota(factory):
    FakeClient.behaviour = {"bad": Quota(), "good": None}
    client = api_keys.RotatingClient(["bad", "good"], FakeClient)
    assert client.models.generate_content(contents="x") == "ok:good"
    assert api_keys.is_exhausted("bad") is True
    assert client.models.generate_content(contents="x") == "ok:good"


def test_rotating_client_raises_when_all_keys_are_out(factory):
    FakeClient.behaviour = {"a": Quota(), "b": Quota()}
    client = api_keys.RotatingClient(["a", "b"], FakeClient)
    with pytest.raises(errors.APIError):
        client.models.generate_content(contents="x")


def test_rotating_client_does_not_hide_other_errors(factory):
    FakeClient.behaviour = {"a": Broken(), "b": None}
    client = api_keys.RotatingClient(["a", "b"], FakeClient)
    with pytest.raises(errors.APIError):
        client.models.generate_content(contents="x")
    assert api_keys.is_exhausted("a") is False


@pytest.fixture
def client(factory, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret")
    monkeypatch.setattr(settings, "demo_mode", False)
    app = FastAPI()
    app.include_router(keys_api.router)
    return TestClient(app)


def test_api_add_list_delete(client):
    r = client.post("/oracle/keys", json={"key": GOOD})
    assert r.status_code == 201 and r.json()["hint"] == "...xxxx"
    listing = client.get("/oracle/keys")
    assert listing.json()["count"] == 1 and GOOD not in listing.text
    kid = listing.json()["keys"][0]["id"]
    assert client.delete(f"/oracle/keys/{kid}").status_code == 200
    assert client.delete(f"/oracle/keys/{kid}").status_code == 404


def test_api_bad_input_and_no_api_key(client, monkeypatch):
    assert client.post("/oracle/keys", json={"key": "short"}).status_code == 422
    monkeypatch.setattr(settings, "api_key", "")
    assert client.post("/oracle/keys", json={"key": GOOD}).status_code == 403
    assert client.delete("/oracle/keys/1").status_code == 403
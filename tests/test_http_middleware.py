import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.middleware import add_http_middleware
from app.core.logging_setup import JsonFormatter, configure_logging, request_id_var
from app.core.security_checks import security_warnings


@pytest.fixture
def client():
    app = FastAPI()
    add_http_middleware(app)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    return TestClient(app)


def test_adds_request_id_and_security_headers(client):
    r = client.get("/ok")
    assert r.status_code == 200
    assert len(r.headers["x-request-id"]) == 32
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


def test_valid_incoming_request_id_is_kept_and_bad_one_replaced(client):
    assert client.get("/ok", headers={"X-Request-ID": "abc-12345"}).headers["x-request-id"] == "abc-12345"
    bad = client.get("/ok", headers={"X-Request-ID": "bad id\twith spaces"})
    assert bad.headers["x-request-id"] != "bad id\twith spaces"
    assert len(bad.headers["x-request-id"]) == 32


def test_unhandled_error_is_hidden_from_client_but_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.http"):
        r = client.get("/boom")
    assert r.status_code == 500
    assert "secret internal detail" not in r.text
    assert r.json()["request_id"] == r.headers["x-request-id"]
    assert any("unhandled error" in rec.getMessage() for rec in caplog.records)


def test_access_log_has_fields_but_no_query_string(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.http"):
        client.get("/ok?token=supersecret")
    record = [r for r in caplog.records if r.getMessage() == "request"][-1]
    assert record.fields["status"] == 200
    assert record.fields["path"] == "/ok"
    assert "supersecret" not in json.dumps(record.fields)


def test_json_formatter_includes_request_id_and_fields():
    token = request_id_var.set("rid-123456")
    try:
        record = logging.LogRecord("app.x", logging.INFO, __file__, 1, "hello %s", ("w",), None)
        record.fields = {"status": 200}
        data = json.loads(JsonFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert data["message"] == "hello w"
    assert data["request_id"] == "rid-123456"
    assert data["status"] == 200 and data["level"] == "INFO"


def test_configure_logging_is_idempotent():
    logger = logging.getLogger("app")
    before = list(logger.handlers)
    try:
        configure_logging("DEBUG", True)
        configure_logging("INFO", True)
        mine = [h for h in logger.handlers if getattr(h, "_briefing", False)]
        assert len(mine) == 1
    finally:
        logger.handlers = before


class Cfg:
    api_key = "k"
    auth_secret = "x" * 40
    dashboard_password = "p"
    debug = False


def test_security_warnings():
    assert security_warnings(Cfg) == []
    cfg = type("Bad", (), {"api_key": "", "auth_secret": "short", "dashboard_password": "", "debug": True})
    assert len(security_warnings(cfg)) == 4
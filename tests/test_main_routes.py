from app.main import app


def test_account_and_core_routes_are_registered():
    paths = set(app.openapi()["paths"])
    assert {"/auth/register", "/auth/login", "/me", "/me/interests"} <= paths
    assert {"/stories", "/chat", "/interests", "/health"} <= paths
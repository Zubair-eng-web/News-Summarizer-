from app.main import app


def test_cleanup_route_is_registered():
    assert "/run-cleanup" in app.openapi()["paths"]
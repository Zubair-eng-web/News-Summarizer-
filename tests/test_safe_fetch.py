import pytest

from app.core.safe_fetch import FetchError, fetch_public


def resolver(host, port):
    ip = "10.0.0.5" if host.startswith("internal") else "93.184.216.34"
    return [(2, 1, 6, "", (ip, port))]


def make_opener(routes):
    def opener(url, timeout, max_bytes):
        return routes[url]
    return opener


def test_returns_body():
    opener = make_opener({"https://a.example/f": (200, {}, b"<rss/>")})
    assert fetch_public("https://a.example/f", opener, resolver) == b"<rss/>"


def test_follows_safe_redirect():
    opener = make_opener({
        "https://a.example/f": (301, {"location": "https://b.example/f2"}, b""),
        "https://b.example/f2": (200, {}, b"ok"),
    })
    assert fetch_public("https://a.example/f", opener, resolver) == b"ok"


def test_blocks_redirect_to_private_host():
    opener = make_opener({
        "https://a.example/f": (302, {"location": "http://internal.example/x"}, b""),
        "http://internal.example/x": (200, {}, b"secret"),
    })
    with pytest.raises(FetchError):
        fetch_public("https://a.example/f", opener, resolver)


def test_blocks_private_start_url():
    with pytest.raises(FetchError):
        fetch_public("http://internal.example/f", make_opener({}), resolver)


def test_too_many_redirects():
    opener = make_opener({"https://a.example/f": (302, {"location": "https://a.example/f"}, b"")})
    with pytest.raises(FetchError):
        fetch_public("https://a.example/f", opener, resolver, max_redirects=2)


def test_too_large():
    opener = make_opener({"https://a.example/f": (200, {}, b"x" * 20)})
    with pytest.raises(FetchError):
        fetch_public("https://a.example/f", opener, resolver, max_bytes=10)


def test_http_error():
    opener = make_opener({"https://a.example/f": (404, {}, b"")})
    with pytest.raises(FetchError):
        fetch_public("https://a.example/f", opener, resolver)

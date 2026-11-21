"""Custom feeds ke liye safe fetch: har redirect hop dobara check hota hai (SSRF)."""
import urllib.error
import urllib.request
from urllib.parse import urljoin

from app.core.user_sources import is_public_url

REDIRECT_CODES = (301, 302, 303, 307, 308)


class FetchError(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _default_open(url: str, timeout: float, max_bytes: int):
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "ai-briefing-agent/1.0"})
    try:
        with opener.open(request, timeout=timeout) as response:
            headers = {k.lower(): v for k, v in response.headers.items()}
            return response.status, headers, response.read(max_bytes + 1)
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, b""


def fetch_public(
    url: str,
    opener=None,
    resolver=None,
    max_redirects: int = 3,
    max_bytes: int = 2_000_000,
    timeout: float = 10.0,
) -> bytes:
    """URL ka body bytes mein. Har hop public hona chahiye, warna FetchError."""
    opener = opener or _default_open
    current = url
    for _ in range(max_redirects + 1):
        if not is_public_url(current, resolver):
            raise FetchError("URL public http(s) nahi hai")
        status, headers, body = opener(current, timeout, max_bytes)
        if status in REDIRECT_CODES:
            location = headers.get("location")
            if not location:
                raise FetchError("Redirect bina Location ke")
            current = urljoin(current, location)
            continue
        if 200 <= status < 300:
            if len(body) > max_bytes:
                raise FetchError("Response bohot bara hai")
            return body
        raise FetchError(f"HTTP {status}")
    raise FetchError("Bohot zyada redirects")

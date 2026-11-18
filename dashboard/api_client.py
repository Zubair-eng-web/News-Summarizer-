import os

import httpx

from app.core.config import settings

DEFAULT_URL = "http://127.0.0.1:8000"
_transport = None  # tests yahan fake transport lagate hain


class ApiError(Exception):
    """API se rabta ya jawab me masla (dashboard ye message seedha dikhata hai)."""


def base_url() -> str:
    return os.getenv("API_URL", DEFAULT_URL).rstrip("/")


def _detail(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        detail = None
    if isinstance(detail, str) and detail:
        return detail
    return f"API error {response.status_code}"


def _forward_headers() -> dict:
    """Dashboard ke visitor ka IP X-Forwarded-For me forward karti hai (rate limit sahi chale)."""
    try:
        import ipaddress

        import streamlit as st

        raw = st.context.headers.get("x-forwarded-for", "")
        first = raw.split(",")[0].strip()
        ipaddress.ip_address(first)  # galat/ganda value ho to ValueError, hum chhor dete hain
    except Exception:
        return {}
    return {"X-Forwarded-For": first}


def _request(
    method: str, path: str, timeout: float = 20.0, extra_headers: dict | None = None, **kwargs
):
    try:
        headers = {"X-API-Key": settings.api_key} if settings.api_key else {}
        headers.update(_forward_headers())
        headers.update(extra_headers or {})
        with httpx.Client(
            base_url=base_url(), timeout=timeout, transport=_transport, headers=headers
        ) as client:
            response = client.request(method, path, **kwargs)
    except httpx.ConnectError:
        raise ApiError(
            "API server se connection nahi ho paya. Pehle server chalayein: "
            "uvicorn app.main:app --reload"
        ) from None
    except httpx.TimeoutException:
        raise ApiError("API ne waqt par jawab nahi diya (timeout). Dobara try karein.") from None
    except httpx.HTTPError as e:
        raise ApiError(f"Network error: {type(e).__name__}") from None

    if response.status_code >= 400:
        raise ApiError(_detail(response))
    return response.json()


def health() -> dict:
    return _request("GET", "/health", timeout=5)


def get_stories(limit: int = 20, priority: str | None = None, hours: int | None = None) -> dict:
    params: dict = {"limit": limit}
    if priority:
        params["priority"] = priority
    if hours:
        params["hours"] = hours
    return _request("GET", "/stories", params=params)


def get_stats() -> dict:
    return _request("GET", "/stats")


def get_articles(limit: int = 50) -> dict:
    return _request("GET", "/articles", params={"limit": limit})


def ask(question: str) -> dict:
    # Chat me 2-3 Gemini calls lagti hain (pehli baar embeddings bhi), is liye lamba timeout
    return _request("POST", "/chat", timeout=90, json={"question": question})


def run_digest() -> dict:
    return _request("POST", "/run-digest")


def run_alerts() -> dict:
    return _request("POST", "/run-alerts")


def get_videos(limit: int = 10) -> dict:
    return _request("GET", "/videos", params={"limit": limit})


def run_videos() -> dict:
    return _request("POST", "/run-videos")


def get_interests() -> dict:
    return _request("GET", "/interests")


def save_interests(interests: str) -> dict:
    return _request("PUT", "/interests", json={"interests": interests})


def research(topic: str) -> dict:
    # 2 Gemini calls + embeddings, is liye lamba timeout
    return _request("POST", "/research", timeout=120, json={"topic": topic})


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register(email: str, password: str) -> dict:
    return _request("POST", "/auth/register", json={"email": email, "password": password})


def login(email: str, password: str) -> dict:
    return _request("POST", "/auth/login", json={"email": email, "password": password})


def my_feed(token: str, limit: int = 20, scope: str = "all") -> dict:
    params: dict = {"limit": limit}
    if scope != "all":
        params["scope"] = scope
    return _request("GET", "/me/feed", params=params, extra_headers=_bearer(token))


def save_my_interests(token: str, interests: str) -> dict:
    return _request(
        "PUT", "/me/interests", json={"interests": interests}, extra_headers=_bearer(token)
    )


def get_delivery(token: str) -> dict:
    return _request("GET", "/me/delivery", extra_headers=_bearer(token))


_UNSET = object()


def save_delivery(
    token: str, digest_enabled=_UNSET, telegram_chat_id=_UNSET, digest_hour=_UNSET
) -> dict:
    """Sirf wahi fields bhejti hai jo di gayi hon (digest_hour=None matlab main digest ke saath)."""
    body = {}
    for key, value in (
        ("digest_enabled", digest_enabled),
        ("telegram_chat_id", telegram_chat_id),
        ("digest_hour", digest_hour),
    ):
        if value is not _UNSET:
            body[key] = value
    return _request("PUT", "/me/delivery", json=body, extra_headers=_bearer(token))


def my_sources(token: str) -> dict:
    return _request("GET", "/me/sources", extra_headers=_bearer(token))


def add_my_source(token: str, kind: str, url: str, name: str) -> dict:
    return _request(
        "POST",
        "/me/sources",
        json={"kind": kind, "url": url, "name": name},
        extra_headers=_bearer(token),
    )


def delete_my_source(token: str, source_id: int) -> dict:
    return _request("DELETE", f"/me/sources/{source_id}", extra_headers=_bearer(token))


def web_check(text: str) -> dict:
    # Web search + Gemini, is liye lamba timeout
    return _request("POST", "/research/web", timeout=90, json={"text": text})


def my_bookmarks(token: str) -> dict:
    return _request("GET", "/me/bookmarks", extra_headers=_bearer(token))


def add_bookmark(token: str, story_id: int) -> dict:
    return _request("PUT", f"/me/bookmarks/{story_id}", extra_headers=_bearer(token))


def remove_bookmark(token: str, story_id: int) -> dict:
    return _request("DELETE", f"/me/bookmarks/{story_id}", extra_headers=_bearer(token))


def related(query: str) -> dict:
    return _request("GET", "/related", params={"q": query})


def oracle_analytics(days: int = 30) -> dict:
    return _request("GET", "/oracle/analytics", params={"days": days})


def oracle_system() -> dict:
    return _request("GET", "/oracle/system")


def oracle_alerts(limit: int = 50) -> dict:
    return _request("GET", "/oracle/alerts", params={"limit": limit})


def oracle_runs(limit: int = 30) -> dict:
    return _request("GET", "/oracle/runs", params={"limit": limit})


def oracle_sources() -> dict:
    return _request("GET", "/oracle/sources")

def my_reads(token: str) -> dict:
    return _request("GET", "/me/reads", extra_headers=_bearer(token))


def mark_read(token: str, story_id: int) -> dict:
    return _request("PUT", f"/me/reads/{story_id}", extra_headers=_bearer(token))


def mark_unread(token: str, story_id: int) -> dict:
    return _request("DELETE", f"/me/reads/{story_id}", extra_headers=_bearer(token))


def oracle_keys() -> dict:
    return _request("GET", "/oracle/keys")


def add_api_key(key: str) -> dict:
    return _request("POST", "/oracle/keys", json={"key": key})


def remove_api_key(key_id: int) -> dict:
    return _request("DELETE", f"/oracle/keys/{key_id}")

"""Signed login tokens (stdlib only: HMAC-SHA256, no extra dependency)."""
import base64
import hashlib
import hmac
import json
import time


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())


def create_token(user_id: int, secret: str, ttl_seconds: int, now: float | None = None) -> str:
    if not secret:
        raise ValueError("AUTH_SECRET set nahi hai")
    current = time.time() if now is None else now
    body = json.dumps({"uid": user_id, "exp": int(current + ttl_seconds)}, separators=(",", ":"))
    payload = _b64(body.encode())
    return f"{payload}.{_sign(payload, secret)}"


def verify_token(token: str, secret: str, now: float | None = None) -> int | None:
    """User id return karta hai, ya None (ghalat, tampered ya expired token)."""
    if not secret or not token or token.count(".") != 1:
        return None
    payload, signature = token.split(".")
    if not hmac.compare_digest(signature, _sign(payload, secret)):
        return None
    try:
        data = json.loads(_unb64(payload))
        user_id, expires = int(data["uid"]), int(data["exp"])
    except Exception:
        return None
    current = time.time() if now is None else now
    return user_id if expires > current else None
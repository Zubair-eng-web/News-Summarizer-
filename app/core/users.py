"""User accounts: password hashing and database access."""
import hashlib
import hmac
import os
import re
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.interests import MAX_INTERESTS, MAX_KEYWORD_LEN, parse_interests
from app.core.models import UserDB, UserPrefDB

ITERATIONS = 240_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserExistsError(Exception):
    pass


def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${_derive(password, salt, ITERATIONS).hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(hash_hex)
        actual = _derive(password, bytes.fromhex(salt_hex), int(iterations))
    except Exception:
        return False
    return hmac.compare_digest(actual, expected)


# Unknown email par bhi same time lagta hai (email guess karna mushkil)
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email)) and len(email) <= 254


def clean_interests(raw: str) -> list[str]:
    seen: list[str] = []
    for k in parse_interests(raw):
        k = k[:MAX_KEYWORD_LEN]
        if k not in seen:
            seen.append(k)
    return seen[:MAX_INTERESTS]


def _to_dict(user: UserDB) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "interests": parse_interests(user.interests),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _open(session_factory):
    return (session_factory or SessionLocal)()


def create_user(email: str, password: str, session_factory=None) -> dict:
    email = normalize_email(email)
    with _open(session_factory) as db:
        user = UserDB(email=email, password_hash=hash_password(password))
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise UserExistsError(email)
        db.refresh(user)
        return _to_dict(user)


def authenticate(email: str, password: str, session_factory=None) -> dict | None:
    email = normalize_email(email)
    with _open(session_factory) as db:
        user = db.query(UserDB).filter(UserDB.email == email).first()
        if user is None:
            verify_password(password, _DUMMY_HASH)
            return None
        return _to_dict(user) if verify_password(password, user.password_hash) else None


def get_user(user_id: int, session_factory=None) -> dict | None:
    with _open(session_factory) as db:
        user = db.get(UserDB, user_id)
        return _to_dict(user) if user else None


def set_user_interests(user_id: int, raw: str, session_factory=None) -> list[str] | None:
    cleaned = clean_interests(raw)
    with _open(session_factory) as db:
        user = db.get(UserDB, user_id)
        if user is None:
            return None
        user.interests = ", ".join(cleaned)
        db.commit()
        return cleaned


def set_digest_enabled(user_id: int, enabled: bool, session_factory=None) -> bool | None:
    with _open(session_factory) as db:
        if db.get(UserDB, user_id) is None:
            return None
        pref = db.get(UserPrefDB, user_id)
        if pref is None:
            pref = UserPrefDB(user_id=user_id)
            db.add(pref)
        pref.digest_enabled = bool(enabled)
        db.commit()
        return bool(enabled)


def get_digest_enabled(user_id: int, session_factory=None) -> bool:
    with _open(session_factory) as db:
        pref = db.get(UserPrefDB, user_id)
        return bool(pref and pref.digest_enabled)


_UNSET = object()
CHAT_ID_RE = re.compile(r"^(-?\d{1,20}|@[A-Za-z][A-Za-z0-9_]{4,31})$")


def clean_chat_id(raw) -> str:
    value = str(raw or "").strip()
    if value and not CHAT_ID_RE.match(value):
        raise ValueError("Telegram chat id sirf number (jaise 123456789) ya @channelname ho sakti hai")
    return value


def clean_digest_hour(raw) -> int | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        raise ValueError("Digest ka waqt 0 se 23 ke beech ghanta ho (UTC)")
    try:
        hour = int(raw)
    except (TypeError, ValueError):
        raise ValueError("Digest ka waqt 0 se 23 ke beech ghanta ho (UTC)") from None
    if not 0 <= hour <= 23:
        raise ValueError("Digest ka waqt 0 se 23 ke beech ghanta ho (UTC)")
    return hour


def _delivery_dict(pref) -> dict:
    return {
        "digest_enabled": bool(pref and pref.digest_enabled),
        "telegram_chat_id": (pref.telegram_chat_id if pref else "") or "",
        "digest_hour": pref.digest_hour if pref else None,
    }


def get_delivery_settings(user_id: int, session_factory=None) -> dict:
    with _open(session_factory) as db:
        return _delivery_dict(db.get(UserPrefDB, user_id))


def update_delivery_settings(
    user_id: int,
    digest_enabled=_UNSET,
    telegram_chat_id=_UNSET,
    digest_hour=_UNSET,
    session_factory=None,
) -> dict | None:
    """Sirf wahi fields badalti hai jo di gayi hon. Galat value par ValueError."""
    chat = clean_chat_id(telegram_chat_id) if telegram_chat_id is not _UNSET else _UNSET
    hour = clean_digest_hour(digest_hour) if digest_hour is not _UNSET else _UNSET
    with _open(session_factory) as db:
        if db.get(UserDB, user_id) is None:
            return None
        pref = db.get(UserPrefDB, user_id)
        if pref is None:
            pref = UserPrefDB(user_id=user_id)
            db.add(pref)
        if digest_enabled is not _UNSET:
            pref.digest_enabled = bool(digest_enabled)
        if chat is not _UNSET:
            pref.telegram_chat_id = chat
        if hour is not _UNSET:
            pref.digest_hour = hour
        pref.updated_at = datetime.utcnow()
        db.commit()
        return _delivery_dict(pref)


def list_digest_recipients(session_factory=None) -> list[dict]:
    """Wo users jinhon ne daily digest on ki hai (delivery settings ke saath)."""
    with _open(session_factory) as db:
        rows = (
            db.query(UserDB, UserPrefDB)
            .join(UserPrefDB, UserPrefDB.user_id == UserDB.id)
            .filter(UserPrefDB.digest_enabled.is_(True))
            .order_by(UserDB.id)
            .all()
        )
        result = []
        for user, pref in rows:
            item = _to_dict(user)
            item["telegram_chat_id"] = pref.telegram_chat_id or ""
            item["digest_hour"] = pref.digest_hour
            result.append(item)
        return result

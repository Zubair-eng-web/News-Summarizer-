"""Gemini API keys: extra keys stored in the database and automatic switching on quota errors."""
import time

from google.genai import errors
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.models import ApiKeyDB

MAX_KEYS = 10
QUOTA_COOLDOWN_SECONDS = 1800  # a key that hit its quota rests for 30 minutes
_exhausted: dict[str, float] = {}


class ApiKeyInputError(Exception):
    pass


def hint(key: str) -> str:
    return "..." + key[-4:] if key else ""


def mark_exhausted(key: str) -> None:
    _exhausted[key] = time.time() + QUOTA_COOLDOWN_SECONDS


def is_exhausted(key: str) -> bool:
    until = _exhausted.get(key)
    if until is None:
        return False
    if until <= time.time():
        _exhausted.pop(key, None)
        return False
    return True


def _open(factory):
    return (factory or SessionLocal)()


def add_key(key: str, factory=None) -> dict:
    key = (key or "").strip()
    if not 20 <= len(key) <= 200 or any(c.isspace() or c in "\"'" for c in key):
        raise ApiKeyInputError("Key sahi nahi lag rahi (20-200 akshar, space ya quotes ke baghair)")
    if factory is None:
        init_db()
    with _open(factory) as db:
        if db.query(ApiKeyDB).count() >= MAX_KEYS:
            raise ApiKeyInputError(f"Zyada se zyada {MAX_KEYS} keys")
        row = ApiKeyDB(key=key)
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ApiKeyInputError("Ye key pehle se add hai") from None
        db.refresh(row)
        return {"id": row.id, "hint": hint(row.key)}


def list_keys(factory=None) -> list[dict]:
    if factory is None:
        init_db()
    with _open(factory) as db:
        rows = db.query(ApiKeyDB).order_by(ApiKeyDB.id).all()
        return [
            {
                "id": r.id,
                "hint": hint(r.key),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "cooling_down": is_exhausted(r.key),
            }
            for r in rows
        ]


def remove_key(key_id: int, factory=None) -> bool:
    if factory is None:
        init_db()
    with _open(factory) as db:
        row = db.get(ApiKeyDB, key_id)
        if row is None:
            return False
        _exhausted.pop(row.key, None)
        db.delete(row)
        db.commit()
        return True


def load_db_keys(factory=None) -> list[str]:
    """Keys saved in the database. Never raises (a broken database means no extra keys)."""
    try:
        if factory is None:
            init_db()
        with _open(factory) as db:
            return [r.key for r in db.query(ApiKeyDB).order_by(ApiKeyDB.id).all()]
    except Exception:
        return []


def candidate_keys(factory=None) -> list[str]:
    """The GEMINI_API_KEY setting first, then the dashboard keys, without duplicates."""
    keys: list[str] = []
    for key in [settings.gemini_api_key, *load_db_keys(factory)]:
        key = (key or "").strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def is_quota_error(error: Exception) -> bool:
    return getattr(error, "code", None) == 429 or "RESOURCE_EXHAUSTED" in str(error)


class _RotatingModels:
    def __init__(self, owner):
        self._owner = owner

    def __getattr__(self, name):
        def call(*args, **kwargs):
            return self._owner._call(name, args, kwargs)

        return call


class RotatingClient:
    """Looks like a genai.Client. On a quota error it retries the call with the next key."""

    def __init__(self, keys, factory):
        self._keys = list(keys)
        self._factory = factory
        self._clients: dict[str, object] = {}

    def _client(self, key):
        if key not in self._clients:
            self._clients[key] = self._factory(api_key=key)
        return self._clients[key]

    def _order(self) -> list[str]:
        live = [k for k in self._keys if not is_exhausted(k)]
        return live or list(self._keys)

    @property
    def models(self):
        return _RotatingModels(self)

    def __getattr__(self, name):
        return getattr(self._client(self._keys[0]), name)

    def _call(self, method, args, kwargs):
        last = None
        for key in self._order():
            try:
                return getattr(self._client(key).models, method)(*args, **kwargs)
            except errors.APIError as e:
                if not is_quota_error(e):
                    raise
                mark_exhausted(key)
                last = e
        raise last
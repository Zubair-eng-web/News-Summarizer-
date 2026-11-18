"""User ke apne RSS feeds aur YouTube channels (validation, storage, loaders)."""
import ipaddress
import re
import socket
from urllib.parse import urlsplit

from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal, init_db
from app.core.models import UserSourceDB

MAX_PER_USER = 8
MAX_EXTRA_PER_KIND = 20
KINDS = ("rss", "youtube")
CHANNEL_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
CHANNEL_IN_URL = re.compile(r"youtube\.com/channel/(UC[A-Za-z0-9_-]{22})")
ALLOWED_PORTS = (None, 80, 443)


class SourceError(ValueError):
    pass


class SourceExistsError(SourceError):
    pass


class SourceLimitError(SourceError):
    pass


def _open(session_factory):
    return (session_factory or SessionLocal)()


def is_public_url(url: str, resolver=None) -> bool:
    """Sirf public http(s) URL. Private, loopback aur link-local addresses band (SSRF)."""
    resolver = resolver or socket.getaddrinfo
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return False
        if parts.username or parts.password:
            return False
        port = parts.port
        if port not in ALLOWED_PORTS:
            return False
        infos = resolver(parts.hostname, port or (443 if parts.scheme == "https" else 80))
        addresses = {info[4][0] for info in infos}
        if not addresses:
            return False
        for address in addresses:
            ip = ipaddress.ip_address(address.split("%")[0])
            if ip.version == 6 and ip.ipv4_mapped:
                ip = ip.ipv4_mapped
            if not ip.is_global:
                return False
    except (ValueError, OSError):
        return False
    return True


def clean_name(name: str) -> str:
    name = re.sub(r"[\x00-\x1f\x7f\[\]<>]", "", name or "")
    return " ".join(name.split())[:60]


def normalize_source(kind: str, url: str, name: str = "", resolver=None) -> tuple[str, str, str]:
    """(kind, url_ya_channel_id, naam) return karta hai, ya SourceError."""
    kind = (kind or "").strip().lower()
    value = (url or "").strip()
    name = clean_name(name)
    if kind == "rss":
        if len(value) > 500 or not is_public_url(value, resolver):
            raise SourceError("Feed ka URL public http(s) hona chahiye")
        if not name:
            raise SourceError("Naam likhna zaroori hai")
        return kind, value, name
    if kind == "youtube":
        if CHANNEL_RE.match(value):
            channel_id = value
        else:
            match = CHANNEL_IN_URL.search(value)
            if not match:
                raise SourceError("YouTube channel ID (UC...) ya /channel/UC... link do")
            channel_id = match.group(1)
        return kind, channel_id, name or channel_id
    raise SourceError("kind rss ya youtube hona chahiye")


def _to_dict(row: UserSourceDB) -> dict:
    return {
        "id": row.id,
        "kind": row.kind,
        "name": row.name,
        "url": row.url,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def add_source(
    user_id: int, kind: str, url: str, name: str = "", session_factory=None, resolver=None
) -> dict:
    kind, value, name = normalize_source(kind, url, name, resolver)
    with _open(session_factory) as db:
        count = db.query(UserSourceDB).filter(UserSourceDB.user_id == user_id).count()
        if count >= MAX_PER_USER:
            raise SourceLimitError(f"Ek user ke liye zyada se zyada {MAX_PER_USER} sources")
        row = UserSourceDB(user_id=user_id, kind=kind, name=name, url=value)
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise SourceExistsError("Ye source aap pehle se add kar chuke hain") from None
        db.refresh(row)
        return _to_dict(row)


def list_sources(user_id: int, session_factory=None) -> list[dict]:
    with _open(session_factory) as db:
        rows = (
            db.query(UserSourceDB)
            .filter(UserSourceDB.user_id == user_id)
            .order_by(UserSourceDB.id)
            .all()
        )
        return [_to_dict(r) for r in rows]


def delete_source(user_id: int, source_id: int, session_factory=None) -> bool:
    with _open(session_factory) as db:
        row = db.get(UserSourceDB, source_id)
        if row is None or row.user_id != user_id:
            return False
        db.delete(row)
        db.commit()
        return True


def _rows(kind: str, session_factory):
    if session_factory is None:
        init_db()
    with _open(session_factory) as db:
        rows = (
            db.query(UserSourceDB)
            .filter(UserSourceDB.kind == kind)
            .order_by(UserSourceDB.id)
            .all()
        )
        return [(r.id, r.name, r.url) for r in rows]


def _build(rows, accept) -> dict[str, str]:
    result: dict[str, str] = {}
    seen: set[str] = set()
    for source_id, name, url in rows:
        if url in seen or not accept(url):
            continue
        seen.add(url)
        key = f"{name} (custom)"
        if key in result:
            key = f"{name} (custom #{source_id})"
        result[key] = url
        if len(result) >= MAX_EXTRA_PER_KIND:
            break
    return result


def load_extra_feeds(session_factory=None, resolver=None) -> dict[str, str]:
    """Sab users ke RSS feeds (naam -> URL). Unsafe URL dobara check hokar skip hota hai."""
    try:
        rows = _rows("rss", session_factory)
    except Exception as e:
        print(f"[WARN] Custom feeds load nahi hui: {type(e).__name__}: {e}")
        return {}
    return _build(rows, lambda url: is_public_url(url, resolver))


def load_extra_channels(session_factory=None) -> dict[str, str]:
    """Sab users ke YouTube channels (naam -> channel ID)."""
    try:
        rows = _rows("youtube", session_factory)
    except Exception as e:
        print(f"[WARN] Custom channels load nahi hue: {type(e).__name__}: {e}")
        return {}
    return _build(rows, lambda channel_id: bool(CHANNEL_RE.match(channel_id)))


def own_source_labels(user_id: int, session_factory=None) -> set[str]:
    """Wo '(custom)' labels jo is user ke apne RSS feeds ki stories par lagte hain.

    Label banane ka rule load_extra_feeds jaisa hi hai: naam se label, ek URL ka ek label,
    aur takrao par '#id'.
    """
    with _open(session_factory) as db:
        rows = (
            db.query(UserSourceDB)
            .filter(UserSourceDB.kind == "rss")
            .order_by(UserSourceDB.id)
            .all()
        )
        data = [(r.id, r.name, r.url, r.user_id) for r in rows]
    by_url: dict[str, str] = {}
    used: set[str] = set()
    mine: set[str] = set()
    for source_id, name, url, owner in data:
        key = by_url.get(url)
        if key is None:
            if len(used) >= MAX_EXTRA_PER_KIND:
                continue
            key = f"{name} (custom)"
            if key in used:
                key = f"{name} (custom #{source_id})"
            by_url[url] = key
            used.add(key)
        if owner == user_id:
            mine.add(key)
    return mine

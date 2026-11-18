"""Account endpoints: register, login, current user, per-user interests."""
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core import ratelimit, user_sources, users
from app.core.ratelimit import client_ip
from app.core.config import settings
from app.core.personalize import hide_foreign_custom, personalize_stories
from app.core.storage import get_recent_stories
from app.core.tokens import create_token, verify_token

router = APIRouter(tags=["accounts"])


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class UserInterests(BaseModel):
    interests: str = Field(default="", max_length=1000)


def _secret() -> str:
    if not settings.auth_secret:
        raise HTTPException(status_code=503, detail="Accounts band hain: AUTH_SECRET set nahi hai")
    return settings.auth_secret


def _throttle(request: Request, email: str | None = None) -> None:
    """Bruteforce rokne ke liye: IP aur (login par) email, dono par limit."""
    limit, window = settings.auth_rate_limit, settings.auth_rate_window_seconds
    keys = [f"auth-ip:{client_ip(request, settings.trust_proxy_headers)}"]
    if email:
        keys.append(f"auth-email:{email[:254]}")
    for key in keys:
        wait = ratelimit.hit(key, limit, window)
        if wait:
            raise HTTPException(
                status_code=429,
                detail="Bohat zyada koshishein. Thori der baad dobara try karein",
                headers={"Retry-After": str(int(wait) + 1)},
            )


def _issue(user: dict) -> dict:
    token = create_token(user["id"], _secret(), settings.auth_token_hours * 3600)
    return {"access_token": token, "token_type": "bearer", "user": user}


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    secret = _secret()
    scheme, _, token = (authorization or "").partition(" ")
    user_id = verify_token(token.strip(), secret) if scheme.lower() == "bearer" else None
    user = users.get_user(user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="Login chahiye ya token expire ho gaya")
    return user


@router.post("/auth/register", status_code=201)
def register(req: Credentials, request: Request):
    _secret()
    _throttle(request)
    email = users.normalize_email(req.email)
    if not users.is_valid_email(email):
        raise HTTPException(status_code=400, detail="Email sahi nahi hai")
    try:
        user = users.create_user(email, req.password)
    except users.UserExistsError:
        raise HTTPException(status_code=409, detail="Ye email pehle se registered hai")
    return _issue(user)


@router.post("/auth/login")
def login(req: Credentials, request: Request):
    _secret()
    _throttle(request, users.normalize_email(req.email))
    user = users.authenticate(req.email, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Email ya password ghalat hai")
    return _issue(user)


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user


@router.put("/me/interests")
def update_my_interests(req: UserInterests, user: dict = Depends(get_current_user)):
    saved = users.set_user_interests(user["id"], req.interests)
    return {"interests": saved or []}


@router.get("/me/feed")
def my_feed(
    limit: int = Query(20, ge=1, le=100),
    scope: str = Query("all", pattern="^(all|mine)$"),
    user: dict = Depends(get_current_user),
):
    """Recent stories re-ranked for this user's interests.

    scope=mine hides stories that come only from other users' custom sources.
    """
    stories = get_recent_stories(limit=100)
    if scope == "mine":
        stories = hide_foreign_custom(stories, user_sources.own_source_labels(user["id"]))
    ranked = personalize_stories(stories, user["interests"])[:limit]
    return {"interests": user["interests"], "scope": scope, "count": len(ranked), "stories": ranked}


class Delivery(BaseModel):
    digest_enabled: bool | None = None
    telegram_chat_id: str | None = Field(default=None, max_length=64)
    digest_hour: int | None = Field(default=None, ge=0, le=23)


def _delivery_payload(user: dict) -> dict:
    return {"email": user["email"], **users.get_delivery_settings(user["id"])}


@router.get("/me/delivery")
def my_delivery(user: dict = Depends(get_current_user)):
    return _delivery_payload(user)


@router.put("/me/delivery")
def update_my_delivery(req: Delivery, user: dict = Depends(get_current_user)):
    """Sirf wahi fields badalti hain jo bheji gayi hon. digest_hour null = main digest ke saath."""
    sent = req.model_fields_set
    changes = {}
    if "digest_enabled" in sent and req.digest_enabled is not None:
        changes["digest_enabled"] = req.digest_enabled
    if "telegram_chat_id" in sent:
        changes["telegram_chat_id"] = req.telegram_chat_id or ""
    if "digest_hour" in sent:
        changes["digest_hour"] = req.digest_hour
    try:
        saved = users.update_delivery_settings(user["id"], **changes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if saved is None:
        raise HTTPException(status_code=404, detail="User nahi mila")
    return _delivery_payload(user)


class SourceIn(BaseModel):
    kind: str = Field(pattern="^(rss|youtube)$")
    url: str = Field(min_length=3, max_length=500)
    name: str = Field(default="", max_length=60)


@router.get("/me/sources")
def my_sources(user: dict = Depends(get_current_user)):
    return {"limit": user_sources.MAX_PER_USER, "sources": user_sources.list_sources(user["id"])}


@router.post("/me/sources", status_code=201)
def add_my_source(req: SourceIn, user: dict = Depends(get_current_user)):
    wait = ratelimit.hit(f"sources:{user['id']}", 30, 3600)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="Bohat zyada koshishein. Thori der baad dobara try karein",
            headers={"Retry-After": str(int(wait) + 1)},
        )
    try:
        return user_sources.add_source(user["id"], req.kind, req.url, req.name)
    except user_sources.SourceExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except user_sources.SourceError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/me/sources/{source_id}")
def delete_my_source(source_id: int, user: dict = Depends(get_current_user)):
    if not user_sources.delete_source(user["id"], source_id):
        raise HTTPException(status_code=404, detail="Source nahi mili")
    return {"deleted": source_id}

"""API key management endpoints. Keys are never returned in full, only a short hint."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core import api_keys, ratelimit
from app.core.config import settings

router = APIRouter(prefix="/oracle/keys", tags=["keys"])


class KeyIn(BaseModel):
    key: str = Field(min_length=20, max_length=200)


def _need_api_key() -> None:
    if not settings.api_key:
        raise HTTPException(
            status_code=403,
            detail="Keys badalne ke liye pehle API_KEY set karein (warna koi bhi badal sakta hai)",
        )


@router.get("")
def list_keys():
    env_key = (settings.gemini_api_key or "").strip()
    keys = api_keys.list_keys()
    return {
        "can_edit": bool(settings.api_key) and not settings.demo_mode,
        "env_key": {"configured": bool(env_key), "hint": api_keys.hint(env_key),
                    "cooling_down": bool(env_key) and api_keys.is_exhausted(env_key)},
        "count": len(keys),
        "limit": api_keys.MAX_KEYS,
        "keys": keys,
    }


@router.post("", status_code=201)
def add_key(req: KeyIn):
    _need_api_key()
    if ratelimit.hit("apikeys-write", 30, 3600):
        raise HTTPException(status_code=429, detail="Bohat zyada koshishein, baad mein try karein")
    try:
        return api_keys.add_key(req.key)
    except api_keys.ApiKeyInputError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{key_id}")
def remove_key(key_id: int):
    _need_api_key()
    if not api_keys.remove_key(key_id):
        raise HTTPException(status_code=404, detail="Key nahi mili")
    return {"deleted": key_id}
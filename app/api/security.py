import hmac

from fastapi import Header, HTTPException

from app.core.config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """API_KEY set ho to har request me X-API-Key header chahiye. Khali ho to koi rok nahi."""
    expected = settings.api_key
    if not expected:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="API key missing ya ghalat hai")

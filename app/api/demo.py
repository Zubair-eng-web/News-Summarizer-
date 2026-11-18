"""Read-only demo mode: DEMO_MODE=true par data badalne wale requests band.

Sirf GET aur do read-only POST (/chat, /research) chalte hain.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
ALLOWED_POSTS = {"/chat", "/research", "/research/web"}


def is_blocked(method: str, path: str) -> bool:
    if method.upper() in SAFE_METHODS:
        return False
    return not (method.upper() == "POST" and path.rstrip("/") in ALLOWED_POSTS)


def add_demo_guard(app: FastAPI) -> None:
    @app.middleware("http")
    async def demo_guard(request: Request, call_next):
        if settings.demo_mode and is_blocked(request.method, request.url.path):
            return JSONResponse(
                {"detail": "Demo mode: ye instance sirf padhne ke liye hai"}, status_code=403
            )
        return await call_next(request)
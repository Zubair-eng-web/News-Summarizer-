"""Web-source check endpoint (Gemini Google Search grounding)."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.agents.research import ResearchError
from app.agents.web_check import web_check
from app.core import ratelimit
from app.core.config import settings
from app.core.ratelimit import client_ip

router = APIRouter()


class WebCheckRequest(BaseModel):
    text: str = Field(min_length=3, max_length=500)


@router.post("/research/web")
def research_web(req: WebCheckRequest, request: Request):
    """Claim ya topic ko web sources se check karta hai (links ke saath)."""
    text = req.text.strip()
    if len(text) < 3:
        raise HTTPException(status_code=400, detail="Text bohat chhota hai")
    wait = ratelimit.hit(f"webcheck:{client_ip(request, settings.trust_proxy_headers)}", 20, 3600)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="Bohat zyada koshishein. Thori der baad dobara try karein",
            headers={"Retry-After": str(int(wait) + 1)},
        )
    try:
        return web_check(text)
    except ValueError as e:  # GEMINI_API_KEY set nahi
        raise HTTPException(status_code=503, detail=str(e))
    except ResearchError as e:
        raise HTTPException(status_code=502, detail=str(e))
"""Request id, access log aur basic security headers."""
import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core import error_alerts
from app.core.logging_setup import request_id_var

log = logging.getLogger("app.http")
_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


def add_http_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_wrapper(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _ID_RE.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        fields = {"method": request.method, "path": request.url.path}
        try:
            try:
                response = await call_next(request)
            except Exception as exc:
                log.exception("unhandled error", extra={"fields": fields})
                error_alerts.report(
                    f"Server error 500: {request.method} {request.url.path}",
                    f"request_id={request_id} error={type(exc).__name__}",
                )
                response = JSONResponse(
                    {"detail": "Server me masla aaya", "request_id": request_id}, status_code=500
                )
            fields["status"] = response.status_code
            fields["duration_ms"] = round((time.perf_counter() - start) * 1000, 1)
            level = logging.DEBUG if request.url.path == "/health" else logging.INFO
            log.log(level, "request", extra={"fields": fields})
            response.headers["X-Request-ID"] = request_id
            for name, value in SECURITY_HEADERS.items():
                response.headers.setdefault(name, value)
            return response
        finally:
            request_id_var.reset(token)
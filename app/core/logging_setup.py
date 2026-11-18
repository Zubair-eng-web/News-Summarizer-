"""Structured (JSON) logging with a per-request id."""
import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

request_id_var = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            data.update(extra)
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """'app' logger par ek handler lagata hai (dobara chalane par duplicate nahi banta)."""
    logger = logging.getLogger("app")
    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    for handler in logger.handlers:
        if getattr(handler, "_briefing", False):
            logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler._briefing = True
    handler.setFormatter(
        JsonFormatter()
        if json_logs
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
"""Telegram notifier for breaking-news alerts.

Never raises: send() returns True/False, so a Telegram problem can
never break the pipeline. The HTTP call is injectable for offline tests.
"""
import json
import os
import urllib.request
from typing import Callable, Optional

API_URL = "https://api.telegram.org/bot{token}/sendMessage"
MAX_LEN = 4096


def _default_post(url: str, payload: dict, timeout: int = 15) -> int:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status


def _read_dotenv(path: str = ".env") -> dict:
    values = {}
    if not os.path.exists(path):
        return values
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class TelegramNotifier:
    def __init__(
        self,
        token: Optional[str],
        chat_id: Optional[str],
        post: Optional[Callable[[str, dict], int]] = None,
    ):
        self.token = (token or "").strip()
        self.chat_id = (chat_id or "").strip()
        self._post = post or _default_post

    @classmethod
    def from_env(cls, post=None) -> "TelegramNotifier":
        dotenv = _read_dotenv()
        token = os.environ.get("TELEGRAM_BOT_TOKEN") or dotenv.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID") or dotenv.get("TELEGRAM_CHAT_ID")
        return cls(token, chat_id, post)

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str) -> bool:
        if not self.enabled or not text:
            return False
        payload = {
            "chat_id": self.chat_id,
            "text": text[:MAX_LEN],
            "disable_web_page_preview": True,
        }
        try:
            status = self._post(API_URL.format(token=self.token), payload)
            return 200 <= int(status) < 300
        except Exception:
            return False


def format_alert(title: str, summary: str, sources: int = 1, url: str = "") -> str:
    credibility = (
        f"Confirmed by {sources} sources" if sources > 1 else "Single source"
    )
    parts = [f"BREAKING: {title}", "", summary.strip(), "", credibility]
    if url:
        parts.append(url)
    return "\n".join(parts)
"""Error alerts (Telegram + email) with a cooldown, so a failing loop never spams.

report() does nothing until install() is called (the server and the scheduler call it),
so tests and scripts never send real messages by accident.
"""
import sys
import threading
import time
from email.message import EmailMessage

from app.core.config import settings

MAX_PER_HOUR = 10

_lock = threading.Lock()
_last: dict[str, float] = {}
_sent_times: list[float] = []
_sender = None


def _default_sender(subject: str, text: str) -> None:
    """Best effort: Telegram aur email dono try hote hain, koi bhi fail ho to chup-chap."""
    try:
        from app.core.telegram_notifier import TelegramNotifier

        TelegramNotifier.from_env().send(f"{subject}\n\n{text}")
    except Exception:
        pass
    try:
        from app.core.mailer import deliver

        def build(sender: str, receiver: str) -> EmailMessage:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = receiver
            msg.set_content(text)
            return msg

        deliver(build)
    except Exception:
        pass


def install(sender=None, force: bool = False) -> bool:
    """Alerts on karta hai. pytest ke andar (force ke baghair) aur ERROR_ALERTS=false par band rehta hai."""
    global _sender
    if not settings.error_alerts:
        return False
    if "pytest" in sys.modules and not force:
        return False
    _sender = sender or _default_sender
    return True


def reset() -> None:
    """Tests ke liye: sab kuch pehli halat par."""
    global _sender
    with _lock:
        _sender = None
        _last.clear()
        _sent_times.clear()


def report(title: str, detail: str = "", sender=None, now: float | None = None) -> bool:
    """True agar alert bheja gaya. Kabhi exception nahi uthata."""
    send = sender or _sender
    if send is None:
        return False
    t = time.monotonic() if now is None else now
    cooldown = max(0, settings.error_alert_cooldown_minutes) * 60
    key = str(title)[:200]
    with _lock:
        _sent_times[:] = [x for x in _sent_times if t - x < 3600]
        if len(_sent_times) >= MAX_PER_HOUR:
            return False
        last = _last.get(key)
        if last is not None and t - last < cooldown:
            return False
        if len(_last) > 200:
            _last.clear()
        _last[key] = t
        _sent_times.append(t)
    try:
        send(f"[ALERT] {key}"[:200], str(detail)[:1500])
        return True
    except Exception:
        return False

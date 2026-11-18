"""Per-user daily digest: har opted-in user ko uski apni interests ke hisab se ranked email.

Optional: user ka apna Telegram chat id (short list) aur apna digest ka ghanta (UTC).
"""
from datetime import datetime

from app.agents.email_agent import build_message
from app.core import users
from app.core.database import init_db
from app.core.mailer import deliver
from app.core.personalize import personalize_stories
from app.core.storage import get_recent_stories, get_setting, set_setting
from app.core.story import Story
from app.core.telegram_notifier import TelegramNotifier

MAX_STORIES = 10
TELEGRAM_STORIES = 5


def dict_to_story(d: dict) -> Story:
    """Database ki story (dict) ko email builder ke Story object me badalta hai."""
    story = Story(
        title=d.get("title", ""),
        summary=d.get("summary", ""),
        sources=[(x["source"], x["link"]) for x in d.get("sources", [])],
    )
    story.priority = d.get("priority", "Medium")
    story.sentiment = d.get("sentiment", "neutral")
    story.credibility = d.get("credibility", "Single source")
    story.claims = d.get("claims", [])
    return story


def _send(stories: list[Story], email: str) -> None:
    deliver(lambda sender, receiver: build_message(stories, sender, receiver), receiver=email)


def telegram_text(stories: list[Story]) -> str:
    lines = ["Aap ki daily briefing", ""]
    for i, s in enumerate(stories[:TELEGRAM_STORIES], 1):
        lines.append(f"{i}. [{s.priority}] {s.title}")
    return "\n".join(lines)


def _telegram_send(chat_id: str, text: str) -> bool:
    notifier = TelegramNotifier.from_env()
    notifier.chat_id = (chat_id or "").strip()
    return notifier.send(text)


def _sent_key(user_id: int) -> str:
    return f"user_digest:{user_id}"


def send_user_digests(
    recipients=None,
    stories=None,
    sender=None,
    already_sent=None,
    mark_sent=None,
    today=None,
    max_stories: int = MAX_STORIES,
    telegram=None,
    now_hour: int | None = None,
    only_scheduled: bool = False,
) -> dict:
    """Har user ko din me ek email. Ek user fail ho to baaki ko email phir bhi jati hai.

    Jis user ne digest_hour set kiya ho, usse pehle us ko digest nahi jati (skipped me ginti hai).
    """
    if recipients is None:
        init_db()
        recipients = users.list_digest_recipients()
    result = {"sent": 0, "skipped": 0, "failed": 0}
    if not recipients:
        return result

    if stories is None:
        stories = get_recent_stories(limit=100, hours=24)
    if not stories:
        result["skipped"] = len(recipients)
        return result

    sender = sender or _send
    telegram = telegram or _telegram_send
    already_sent = already_sent or (lambda uid, day: get_setting(_sent_key(uid)) == day)
    mark_sent = mark_sent or (lambda uid, day: set_setting(_sent_key(uid), day))
    day = today or datetime.utcnow().strftime("%Y-%m-%d")
    hour_now = datetime.utcnow().hour if now_hour is None else now_hour

    for user in recipients:
        if already_sent(user["id"], day):
            result["skipped"] += 1
            continue
        wanted_hour = user.get("digest_hour")
        if only_scheduled and wanted_hour is None:  # inhein main digest ke saath jati hai
            result["skipped"] += 1
            continue
        if wanted_hour is not None and hour_now < wanted_hour:
            result["skipped"] += 1
            continue
        ranked = personalize_stories(stories, user["interests"])[:max_stories]
        items = [dict_to_story(s) for s in ranked]
        try:
            sender(items, user["email"])
            mark_sent(user["id"], day)
            result["sent"] += 1
        except Exception as e:
            print(f"[WARN] User digest fail (user {user['id']}): {type(e).__name__}: {e}")
            result["failed"] += 1
            continue
        chat_id = user.get("telegram_chat_id")
        if chat_id:
            try:
                telegram(chat_id, telegram_text(items))
            except Exception as e:  # Telegram kabhi email ya baaki users ko nahi rokta
                print(f"[WARN] User Telegram fail (user {user['id']}): {type(e).__name__}")
    return result

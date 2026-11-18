import re
import socket
from datetime import datetime
from typing import Optional

import feedparser

from app.core import source_health
from app.core.user_sources import load_extra_channels
from app.core.video import Video

socket.setdefaulttimeout(10)

FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"

# Channel name -> channel ID (UC...). Apne pasandeeda channels yahan jod sakte hain.
CHANNELS = {
    "BBC News": "UC16niRr50-MSBwiO3YDb3RA",
    "Al Jazeera English": "UCNye-wNBqNL5ZzHSJj3l8Bg",
    "DW News": "UCknLrEdhRCp1aegoMqRaCZg",
    "Fireship": "UCsBjURrPoezykLs9EqgamOA",
}

PREFERRED_LANGUAGES = ("en", "ur", "hi")
_ID = r"[A-Za-z0-9_-]{11}"


class TranscriptError(Exception):
    """Transcript nahi mila (captions band, video unavailable, ya YouTube ne rok diya)."""


def extract_video_id(value: str) -> Optional[str]:
    """YouTube URL ya seedhi ID se 11-character video ID nikalta hai."""
    value = (value or "").strip()
    if re.fullmatch(_ID, value):
        return value
    match = re.search(r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)(" + _ID + ")", value)
    return match.group(1) if match else None


def fetch_channel(
    name: str, channel_id: str, limit: int = 5, parser=feedparser.parse
) -> list[Video]:
    """Ek channel ke naye videos. Fail ho to khali list (baaqi channels chalte rehte hain)."""
    try:
        feed = parser(FEED_URL.format(channel_id))
    except Exception as e:
        print(f"[ERROR] YouTube {name}: {e}")
        return []

    if not feed.entries:
        print(f"[WARN] YouTube {name}: koi video nahi mila (channel ID check karein)")
        return []

    videos: list[Video] = []
    for entry in feed.entries[:limit]:
        link = entry.get("link", "")
        video_id = entry.get("yt_videoid") or extract_video_id(link)
        if not video_id:
            continue
        published = None
        parsed = entry.get("published_parsed")
        if parsed:
            published = datetime(*parsed[:6])
        videos.append(
            Video(
                video_id=video_id,
                title=" ".join(entry.get("title", "").split()),
                link=link or f"https://www.youtube.com/watch?v={video_id}",
                channel=name,
                published=published,
                description=(entry.get("summary", "") or "")[:1000],
            )
        )
    return videos


def is_short(video: Video) -> bool:
    """YouTube Shorts: bohat chhote clips, aksar bina transcript ke."""
    return "/shorts/" in video.link or "#shorts" in video.title.lower()


def collect_videos(
    limit_per_channel: int = 3,
    channels=None,
    fetcher=fetch_channel,
    include_shorts: bool = False,
    include_custom: bool | None = None,
) -> list[Video]:
    """Saare channels ke videos, naye pehle, duplicate IDs ke baghair. Shorts default me nahi."""
    if include_custom is None:
        include_custom = channels is None and fetcher is fetch_channel
    channels = channels or CHANNELS
    if include_custom:
        channels = {**channels, **load_extra_channels()}
    # Shorts hatane ke baad bhi kaafi videos bachein, is liye zyada fetch karte hain
    fetch_limit = limit_per_channel if include_shorts else limit_per_channel * 3

    seen: set[str] = set()
    videos: list[Video] = []
    for name, channel_id in channels.items():
        kept = 0
        fetched = fetcher(name, channel_id, fetch_limit)
        if fetched:
            source_health.record(name, "youtube", True, len(fetched))
        else:
            source_health.record(
                name, "youtube", False, 0,
                "No videos returned (wrong channel ID, blocked or empty)",
            )
        for video in fetched:
            if kept >= limit_per_channel:
                break
            if not include_shorts and is_short(video):
                continue
            if video.video_id in seen:
                continue
            seen.add(video.video_id)
            videos.append(video)
            kept += 1
    videos.sort(key=lambda v: v.published or datetime.min, reverse=True)
    return videos


def _first_line(error: Exception) -> str:
    lines = str(error).strip().splitlines()
    return f"{type(error).__name__}: {lines[0][:120]}" if lines else type(error).__name__


def fetch_transcript(video_id: str, languages=PREFERRED_LANGUAGES, api=None) -> str:
    """Video ka transcript ek text me. Masla ho to TranscriptError."""
    try:
        if api is None:
            from youtube_transcript_api import YouTubeTranscriptApi

            api = YouTubeTranscriptApi()
        snippets = api.fetch(video_id, languages=list(languages))
        parts = []
        for s in snippets:
            parts.append(s.get("text", "") if isinstance(s, dict) else getattr(s, "text", ""))
    except Exception as e:
        raise TranscriptError(_first_line(e)) from e

    text = " ".join(parts)
    text = re.sub(r"\[[^\]]*\]", " ", text)  # [Music], [Applause] jaise nishan
    text = " ".join(text.split())
    if not text:
        raise TranscriptError("Transcript khali hai")
    return text


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if "--transcript" in args:
        rest = [a for a in args if a != "--transcript"]
        if rest:
            video_id = extract_video_id(rest[0])
            if not video_id:
                print("Ye valid YouTube link ya video ID nahi hai")
                raise SystemExit(1)
            candidates = [video_id]
        else:
            candidates = [v.video_id for v in collect_videos(2)]

        for video_id in candidates[:8]:
            try:
                text = fetch_transcript(video_id)
            except TranscriptError as e:
                print(f"[SKIP] {video_id}: {e}")
                continue
            print(f"\nVideo: https://youtu.be/{video_id}")
            print(f"Transcript length: {len(text)} characters")
            print(f"Preview: {text[:300]}")
            break
        else:
            print("\nKisi video ka transcript nahi mila")
    else:
        videos = collect_videos(limit_per_channel=2)
        print(f"\nTotal videos: {len(videos)}\n")
        for v in videos:
            when = v.published.strftime("%Y-%m-%d %H:%M") if v.published else "-"
            print(f"[{v.channel}] {v.title}")
            print(f"   {when}  {v.link}\n")

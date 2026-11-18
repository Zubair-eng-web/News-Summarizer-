from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Video:
    video_id: str
    title: str
    link: str
    channel: str
    published: Optional[datetime] = None
    description: str = ""


@dataclass
class VideoSummary:
    video_id: str
    title: str
    link: str
    channel: str
    published: Optional[datetime] = None
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    takeaway: str = ""
    has_transcript: bool = False

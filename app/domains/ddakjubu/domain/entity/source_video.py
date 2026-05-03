from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SourceVideo:
    video_id: str
    title: str
    description: str
    transcript: str
    channel_id: str
    channel_name: str
    published_at: datetime
    collected_at: datetime
    video_url: str = ""
    program_category: Optional[str] = field(default=None)
    summary: str = ""

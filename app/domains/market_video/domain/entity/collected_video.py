from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CollectedVideo:
    video_id: str
    title: str
    channel_name: str
    published_at: datetime
    view_count: int
    thumbnail_url: str
    video_url: str
    id: Optional[int] = None

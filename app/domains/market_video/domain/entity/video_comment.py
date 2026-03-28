from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class VideoComment:
    comment_id: str
    video_id: str
    author_name: str
    content: str
    published_at: datetime
    like_count: int
    id: Optional[int] = field(default=None)

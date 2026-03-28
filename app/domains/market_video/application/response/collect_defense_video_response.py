from datetime import datetime

from pydantic import BaseModel


class CollectedVideoItemResponse(BaseModel):
    video_id: str
    title: str
    channel_name: str
    published_at: datetime
    view_count: int
    thumbnail_url: str
    video_url: str


class CollectDefenseVideoResponse(BaseModel):
    saved_count: int
    videos: list[CollectedVideoItemResponse]

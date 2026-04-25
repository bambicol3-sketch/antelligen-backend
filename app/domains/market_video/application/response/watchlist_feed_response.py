from typing import Optional

from pydantic import BaseModel


class FeedVideoItem(BaseModel):
    video_id: Optional[str] = None
    title: str
    thumbnail_url: str
    channel_name: str
    published_at: str
    video_url: str


class WatchlistYoutubeFeedResponse(BaseModel):
    has_watchlist: bool
    watchlist_keywords: list[str]
    items: list[FeedVideoItem]
    next_page_token: Optional[str] = None
    total_results: int

from typing import Optional

import httpx

from app.domains.market_video.application.port.out.youtube_video_provider import (
    YoutubeVideoProvider,
    YoutubeVideoSearchResult,
)
from app.domains.market_video.domain.entity.video_item import VideoItem

SEARCH_KEYWORD = "주식 경제 증시 투자"
MAX_RESULTS = 9


class YoutubeVideoClient(YoutubeVideoProvider):
    BASE_URL = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search(self, page_token: Optional[str] = None) -> YoutubeVideoSearchResult:
        params = {
            "key": self._api_key,
            "q": SEARCH_KEYWORD,
            "part": "snippet",
            "type": "video",
            "maxResults": MAX_RESULTS,
            "regionCode": "KR",
            "relevanceLanguage": "ko",
            "order": "date",
        }
        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        items = []
        for item in data.get("items", []):
            video_id = item.get("id", {}).get("videoId", "")
            snippet = item.get("snippet", {})
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url", "")
            )
            items.append(VideoItem(
                video_id=video_id,
                title=snippet.get("title", ""),
                thumbnail_url=thumbnail_url,
                channel_name=snippet.get("channelTitle", ""),
                published_at=snippet.get("publishedAt", ""),
                video_url=f"https://www.youtube.com/watch?v={video_id}",
            ))

        return YoutubeVideoSearchResult(
            items=items,
            next_page_token=data.get("nextPageToken"),
            prev_page_token=data.get("prevPageToken"),
            total_results=data.get("pageInfo", {}).get("totalResults", 0),
        )

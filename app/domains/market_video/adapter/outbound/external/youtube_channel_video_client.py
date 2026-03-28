import logging
from datetime import datetime

import httpx

from app.domains.market_video.application.port.out.channel_video_fetch_port import (
    ChannelVideoFetchPort,
    ChannelVideoItem,
)

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


class YoutubeChannelVideoClient(ChannelVideoFetchPort):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def fetch_recent_videos(
        self,
        channel_ids: list[str],
        published_after: datetime,
        max_per_channel: int = 10,
    ) -> list[ChannelVideoItem]:
        published_after_str = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")
        all_video_ids: list[str] = []
        snippets: dict[str, dict] = {}

        async with httpx.AsyncClient(timeout=10.0) as client:
            for channel_id in channel_ids:
                try:
                    params = {
                        "key": self._api_key,
                        "channelId": channel_id,
                        "part": "snippet",
                        "type": "video",
                        "maxResults": max_per_channel,
                        "publishedAfter": published_after_str,
                        "order": "date",
                    }
                    response = await client.get(SEARCH_URL, params=params)
                    if response.status_code != 200:
                        logger.warning("[youtube_channel] channel=%s status=%s", channel_id, response.status_code)
                        continue
                    data = response.json()
                    for item in data.get("items", []):
                        video_id = item.get("id", {}).get("videoId", "")
                        if video_id:
                            all_video_ids.append(video_id)
                            snippets[video_id] = item.get("snippet", {})
                except Exception as e:
                    logger.warning("[youtube_channel] channel=%s error=%s", channel_id, e)
                    continue

            view_counts: dict[str, int] = {}
            for i in range(0, len(all_video_ids), 50):
                batch = all_video_ids[i:i + 50]
                try:
                    stats_params = {
                        "key": self._api_key,
                        "id": ",".join(batch),
                        "part": "statistics",
                    }
                    stats_response = await client.get(VIDEOS_URL, params=stats_params)
                    if stats_response.status_code == 200:
                        for item in stats_response.json().get("items", []):
                            vid_id = item.get("id", "")
                            view_counts[vid_id] = int(
                                item.get("statistics", {}).get("viewCount", 0)
                            )
                except Exception as e:
                    logger.warning("[youtube_channel] statistics fetch error=%s", e)

        result = []
        for video_id in all_video_ids:
            snippet = snippets.get(video_id, {})
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url", "")
            )
            published_at_str = snippet.get("publishedAt", "")
            try:
                published_at = datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ")
            except (ValueError, TypeError):
                published_at = datetime.utcnow()

            result.append(ChannelVideoItem(
                video_id=video_id,
                title=snippet.get("title", ""),
                channel_name=snippet.get("channelTitle", ""),
                published_at=published_at,
                view_count=view_counts.get(video_id, 0),
                thumbnail_url=thumbnail_url,
                video_url=f"https://www.youtube.com/watch?v={video_id}",
            ))

        return result

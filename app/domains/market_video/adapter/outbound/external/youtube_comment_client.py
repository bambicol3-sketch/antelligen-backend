import logging
from datetime import datetime

import httpx

from app.domains.market_video.application.port.out.comment_fetch_port import CommentFetchPort, CommentItem

logger = logging.getLogger(__name__)

COMMENT_THREADS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"


class YoutubeCommentClient(CommentFetchPort):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def fetch_comments(
        self,
        video_id: str,
        max_count: int = 20,
        order: str = "relevance",
    ) -> list[CommentItem]:
        collected: list[CommentItem] = []
        page_token: str | None = None

        async with httpx.AsyncClient(timeout=10.0) as client:
            while len(collected) < max_count:
                remaining = max_count - len(collected)
                params = {
                    "key": self._api_key,
                    "videoId": video_id,
                    "part": "snippet",
                    "maxResults": min(remaining, 100),
                    "order": order,
                }
                if page_token:
                    params["pageToken"] = page_token

                response = await client.get(COMMENT_THREADS_URL, params=params)

                if response.status_code == 403:
                    logger.info("[youtube_comment] 댓글 비활성화 또는 접근 불가 video_id=%s", video_id)
                    return []
                if response.status_code == 404:
                    logger.info("[youtube_comment] 유효하지 않은 영상 video_id=%s", video_id)
                    return []
                if response.status_code != 200:
                    logger.warning("[youtube_comment] video_id=%s status=%s", video_id, response.status_code)
                    return []

                data = response.json()

                for item in data.get("items", []):
                    top = item.get("snippet", {}).get("topLevelComment", {})
                    comment_id = top.get("id", "")
                    snippet = top.get("snippet", {})
                    content = snippet.get("textOriginal", "").strip()

                    if not content:
                        continue

                    published_at_str = snippet.get("publishedAt", "")
                    try:
                        published_at = datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ")
                    except (ValueError, TypeError):
                        published_at = datetime.utcnow()

                    collected.append(CommentItem(
                        comment_id=comment_id,
                        author_name=snippet.get("authorDisplayName", ""),
                        content=content,
                        published_at=published_at,
                        like_count=int(snippet.get("likeCount", 0)),
                    ))

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        return collected

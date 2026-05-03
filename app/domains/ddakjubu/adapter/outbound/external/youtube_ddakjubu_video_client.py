import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.domains.ddakjubu.application.port.ddakjubu_video_fetch_port import DdakjubuVideoFetchPort
from app.domains.ddakjubu.domain.entity.source_video import SourceVideo

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


class YoutubeDdakjubuVideoClient(DdakjubuVideoFetchPort):
    """YouTube Data API v3을 이용해 딱주부TV 학습프로그램 영상을 조회한다.

    channel 내 검색(search.list)을 사용해 program_filters 키워드에 해당하는
    영상을 찾고, videos.list로 상세(설명 등)을 보강한다.
    """

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def fetch_learning_videos(
        self,
        channel_ids: List[str],
        program_filters: List[str],
        max_results_per_channel: int = 20,
    ) -> List[SourceVideo]:
        if not channel_ids:
            return []

        collected: List[SourceVideo] = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for channel_id in channel_ids:
                for query in program_filters:
                    try:
                        items = await self._search_channel_videos(
                            client, channel_id, query, max_results_per_channel
                        )
                    except Exception as e:
                        logger.warning(
                            "[ddakjubu_youtube] search 실패 channel=%s query=%s error=%s",
                            channel_id,
                            query,
                            e,
                        )
                        continue

                    if not items:
                        continue

                    video_ids = [
                        item.get("id", {}).get("videoId")
                        for item in items
                        if item.get("id", {}).get("videoId")
                    ]
                    if not video_ids:
                        continue

                    details = await self._fetch_video_details(client, video_ids)

                    for item in items:
                        video_id = item.get("id", {}).get("videoId")
                        if not video_id or video_id not in details:
                            continue

                        detail = details[video_id]
                        snippet = detail.get("snippet", {}) or item.get("snippet", {})
                        title = snippet.get("title", "")
                        description = snippet.get("description", "")
                        channel_name = snippet.get("channelTitle", "")
                        published_at = self._parse_datetime(snippet.get("publishedAt"))

                        if not self._matches_program(title, description, program_filters):
                            continue

                        collected.append(
                            SourceVideo(
                                video_id=video_id,
                                title=title,
                                description=description,
                                transcript="",
                                channel_id=channel_id,
                                channel_name=channel_name,
                                published_at=published_at,
                                collected_at=datetime.now(timezone.utc),
                                video_url=f"https://www.youtube.com/watch?v={video_id}",
                                program_category=self._classify_program(title, program_filters),
                            )
                        )

        return collected

    async def _search_channel_videos(
        self,
        client: httpx.AsyncClient,
        channel_id: str,
        query: str,
        max_results: int,
    ) -> List[dict]:
        response = await client.get(
            YOUTUBE_SEARCH_URL,
            params={
                "key": self._api_key,
                "channelId": channel_id,
                "q": query,
                "part": "snippet",
                "type": "video",
                "order": "date",
                "maxResults": max_results,
            },
        )
        if response.status_code != 200:
            logger.warning(
                "[ddakjubu_youtube] search status=%s body=%s",
                response.status_code,
                response.text[:200],
            )
            return []
        return response.json().get("items", [])

    async def _fetch_video_details(
        self,
        client: httpx.AsyncClient,
        video_ids: List[str],
    ) -> dict:
        result: dict = {}
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            try:
                response = await client.get(
                    YOUTUBE_VIDEOS_URL,
                    params={
                        "key": self._api_key,
                        "id": ",".join(batch),
                        "part": "snippet,contentDetails",
                    },
                )
                if response.status_code != 200:
                    continue
                for item in response.json().get("items", []):
                    vid = item.get("id")
                    if vid:
                        result[vid] = item
            except Exception as e:
                logger.warning("[ddakjubu_youtube] videos.list 실패 error=%s", e)
                continue
        return result

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)

    @staticmethod
    def _matches_program(title: str, description: str, program_filters: List[str]) -> bool:
        haystack = f"{title}\n{description}".lower()
        return any(keyword.lower() in haystack for keyword in program_filters)

    @staticmethod
    def _classify_program(title: str, program_filters: List[str]) -> str:
        lowered = title.lower()
        for keyword in program_filters:
            if keyword.lower() in lowered:
                return keyword
        return "학습프로그램"

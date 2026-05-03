from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.domains.ddakjubu2.application.port.ddakjubu2_video_fetch_port import (
    Ddakjubu2VideoFetchPort,
)
from app.domains.ddakjubu2.domain.entity.source_video import SourceVideo

YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

PAGE_SIZE = 50


class YoutubeDdakjubu2VideoClient(Ddakjubu2VideoFetchPort):
    """YouTube Data API v3 을 이용해 딱주부TV 채널의 영상을 조회한다.

    channels.list 로 채널의 uploads 플레이리스트 ID 를 얻고,
    playlistItems.list 로 페이지네이션 전체를 순회하며 published_after 하한까지
    수집한다. videos.list 로 상세 정보(설명 등) 를 보강한다.
    """

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def fetch_channel_videos(
        self,
        channel_ids: List[str],
        published_after: Optional[datetime] = None,
    ) -> List[SourceVideo]:
        if not channel_ids:
            print("[ddakjubu2_youtube] 채널 목록이 비어있어 조회하지 않음")
            return []

        collected: List[SourceVideo] = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            for channel_id in channel_ids:
                print(
                    f"[ddakjubu2_youtube] 채널 조회 시작: {channel_id} "
                    f"published_after={published_after.isoformat() if published_after else 'None'}"
                )
                uploads_playlist_id = await self._get_uploads_playlist_id(
                    client, channel_id
                )
                if not uploads_playlist_id:
                    print(
                        f"[ddakjubu2_youtube] uploads 플레이리스트를 찾지 못함: "
                        f"channel_id={channel_id}"
                    )
                    continue

                playlist_items = await self._fetch_playlist_items(
                    client, uploads_playlist_id, published_after
                )
                print(
                    f"[ddakjubu2_youtube] playlistItems 수집 결과 수="
                    f"{len(playlist_items)} channel_id={channel_id}"
                )
                if not playlist_items:
                    continue

                video_ids = [
                    item.get("contentDetails", {}).get("videoId")
                    for item in playlist_items
                    if item.get("contentDetails", {}).get("videoId")
                ]
                if not video_ids:
                    continue

                details = await self._fetch_video_details(client, video_ids)

                for item in playlist_items:
                    video_id = item.get("contentDetails", {}).get("videoId")
                    if not video_id:
                        continue

                    detail = details.get(video_id, {})
                    snippet = detail.get("snippet") or item.get("snippet", {})

                    title = snippet.get("title", "")
                    description = snippet.get("description", "")
                    channel_name = snippet.get("channelTitle", "")
                    published_at = self._parse_datetime(snippet.get("publishedAt"))

                    if published_after and published_at < published_after:
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
                            program_category="전체영상",
                        )
                    )

        print(f"[ddakjubu2_youtube] 총 수집된 영상 수={len(collected)}")
        return collected

    async def _get_uploads_playlist_id(
        self,
        client: httpx.AsyncClient,
        channel_id: str,
    ) -> Optional[str]:
        try:
            response = await client.get(
                YOUTUBE_CHANNELS_URL,
                params={
                    "key": self._api_key,
                    "id": channel_id,
                    "part": "contentDetails",
                },
            )
        except Exception as e:
            print(f"[ddakjubu2_youtube] channels.list 호출 실패 error={e}")
            return None

        if response.status_code != 200:
            print(
                f"[ddakjubu2_youtube] channels.list status={response.status_code} "
                f"body={response.text[:200]}"
            )
            return None

        items = response.json().get("items", [])
        if not items:
            return None
        return (
            items[0]
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )

    async def _fetch_playlist_items(
        self,
        client: httpx.AsyncClient,
        playlist_id: str,
        published_after: Optional[datetime],
    ) -> List[dict]:
        """uploads 플레이리스트의 모든 페이지를 순회한다.

        uploads 플레이리스트는 최신순으로 반환되므로, published_after 하한이
        주어지면 그 하한보다 오래된 항목이 한 페이지라도 감지되는 순간
        페이지네이션을 중단해 불필요한 쿼터 사용을 막는다.
        """
        items: List[dict] = []
        page_token: Optional[str] = None
        page_index = 0

        while True:
            page_index += 1
            params = {
                "key": self._api_key,
                "playlistId": playlist_id,
                "part": "snippet,contentDetails",
                "maxResults": PAGE_SIZE,
            }
            if page_token:
                params["pageToken"] = page_token

            try:
                response = await client.get(YOUTUBE_PLAYLIST_ITEMS_URL, params=params)
            except Exception as e:
                print(f"[ddakjubu2_youtube] playlistItems 호출 실패 error={e}")
                break

            if response.status_code != 200:
                print(
                    f"[ddakjubu2_youtube] playlistItems status={response.status_code} "
                    f"body={response.text[:200]}"
                )
                break

            payload = response.json()
            page_items = payload.get("items", [])
            if not page_items:
                break

            items.extend(page_items)
            print(
                f"[ddakjubu2_youtube] 페이지 {page_index} 수신: +{len(page_items)} "
                f"(누적 {len(items)})"
            )

            if published_after is not None:
                oldest_in_page = self._oldest_published_at(page_items)
                if oldest_in_page is not None and oldest_in_page < published_after:
                    print(
                        f"[ddakjubu2_youtube] 하한 도달 oldest={oldest_in_page.isoformat()} "
                        f"cutoff={published_after.isoformat()} → 페이지네이션 중단"
                    )
                    break

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return items

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
            except Exception as e:
                print(f"[ddakjubu2_youtube] videos.list 호출 실패 error={e}")
                continue

            if response.status_code != 200:
                print(
                    f"[ddakjubu2_youtube] videos.list status={response.status_code} "
                    f"body={response.text[:200]}"
                )
                continue

            for item in response.json().get("items", []):
                vid = item.get("id")
                if vid:
                    result[vid] = item
        return result

    @classmethod
    def _oldest_published_at(cls, page_items: List[dict]) -> Optional[datetime]:
        oldest: Optional[datetime] = None
        for item in page_items:
            snippet = item.get("snippet", {})
            parsed = cls._parse_datetime(snippet.get("publishedAt"))
            if oldest is None or parsed < oldest:
                oldest = parsed
        return oldest

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
        return datetime.now(timezone.utc)

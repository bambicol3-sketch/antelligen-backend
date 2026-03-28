import logging
from datetime import datetime, timedelta

from app.domains.market_video.application.port.out.channel_video_fetch_port import ChannelVideoFetchPort
from app.domains.market_video.application.port.out.collected_video_repository_port import CollectedVideoRepositoryPort
from app.domains.market_video.application.response.collect_defense_video_response import (
    CollectDefenseVideoResponse,
    CollectedVideoItemResponse,
)
from app.domains.market_video.domain.entity.collected_video import CollectedVideo

logger = logging.getLogger(__name__)

TARGET_CHANNEL_IDS = [
    "UCF8AeLlUbEpKju6v1H6p8Eg",  # 한국경제TV
    "UCbMjg2EvXs_RUGW-KrdM3pw",  # SBS Biz
    "UCTHCOPwqNfZ0uiKOvFyhGwg",  # 연합뉴스TV
    "UCcQTRi69dsVYHN3exePtZ1A",  # KBS News
    "UCG9aFJTZ-lMCHAiO1KJsirg",  # MBN
    "UCsU-I-vHLiaMfV_ceaYz5rQ",  # JTBC News
    "UClErHbdZKUnD1NyIUeQWvuQ",  # 머니투데이
    "UC8Sv6O3Ux8ePVqorx8aOBMg",  # 이데일리TV
    "UCnfwIKyFYRuqZzzKBDt6JOA",  # 매일경제TV
]

DEFENSE_KEYWORDS = [
    "전쟁", "군사", "미사일", "방위산업", "무기", "NATO", "국방",
    "방산", "전투", "군비", "핵", "탄도", "안보", "무장", "K방산",
    "방공", "육군", "해군", "공군", "해병", "폭격", "함정", "전차",
]

PUBLISHED_AFTER_DAYS = 7
MAX_PER_CHANNEL = 10
TOP_N = 10


class CollectDefenseVideoUseCase:
    def __init__(
        self,
        channel_video_fetch_port: ChannelVideoFetchPort,
        collected_video_repository_port: CollectedVideoRepositoryPort,
    ):
        self._fetch_port = channel_video_fetch_port
        self._repository = collected_video_repository_port

    async def execute(self) -> CollectDefenseVideoResponse:
        if not TARGET_CHANNEL_IDS:
            return CollectDefenseVideoResponse(saved_count=0, videos=[])

        published_after = datetime.utcnow() - timedelta(days=PUBLISHED_AFTER_DAYS)

        raw_videos = await self._fetch_port.fetch_recent_videos(
            channel_ids=TARGET_CHANNEL_IDS,
            published_after=published_after,
            max_per_channel=MAX_PER_CHANNEL,
        )

        filtered = [v for v in raw_videos if self._contains_defense_keyword(v.title)]

        if not filtered:
            return CollectDefenseVideoResponse(saved_count=0, videos=[])

        sorted_videos = sorted(filtered, key=lambda v: v.published_at, reverse=True)[:TOP_N]

        saved = []
        for item in sorted_videos:
            try:
                video = CollectedVideo(
                    video_id=item.video_id,
                    title=item.title,
                    channel_name=item.channel_name,
                    published_at=item.published_at,
                    view_count=item.view_count,
                    thumbnail_url=item.thumbnail_url,
                    video_url=item.video_url,
                )
                result = await self._repository.upsert(video)
                saved.append(result)
            except Exception as e:
                logger.warning("[collect_defense_video] 저장 실패 video_id=%s: %s", item.video_id, e)
                continue

        videos = [
            CollectedVideoItemResponse(
                video_id=v.video_id,
                title=v.title,
                channel_name=v.channel_name,
                published_at=v.published_at,
                view_count=v.view_count,
                thumbnail_url=v.thumbnail_url,
                video_url=v.video_url,
            )
            for v in saved
        ]

        return CollectDefenseVideoResponse(saved_count=len(saved), videos=videos)

    @staticmethod
    def _contains_defense_keyword(title: str) -> bool:
        return any(keyword in title for keyword in DEFENSE_KEYWORDS)

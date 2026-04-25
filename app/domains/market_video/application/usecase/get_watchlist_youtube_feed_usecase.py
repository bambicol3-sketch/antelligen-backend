import asyncio
from typing import Optional
from urllib.parse import parse_qs, urlparse

from app.domains.account.application.port.out.watchlist_repository_port import WatchlistRepositoryPort
from app.domains.market_video.application.port.youtube_search_port import YoutubeSearchPort
from app.domains.market_video.application.response.watchlist_feed_response import (
    FeedVideoItem,
    WatchlistYoutubeFeedResponse,
)
from app.domains.stock_theme.domain.value_object.theme_name import MAIN_THEMES

_DEFAULT_KEYWORDS = [f"{t} 주식" for t in MAIN_THEMES]
PAGE_SIZE = 9


def _extract_video_id(video_url: str) -> Optional[str]:
    try:
        qs = parse_qs(urlparse(video_url).query)
        return qs.get("v", [None])[0]
    except Exception:
        return None


class GetWatchlistYoutubeFeedUseCase:
    def __init__(
        self,
        youtube_search_port: YoutubeSearchPort,
        watchlist_port: WatchlistRepositoryPort,
    ):
        self._search_port = youtube_search_port
        self._watchlist_port = watchlist_port

    async def execute(
        self,
        account_id: Optional[int],
        page_token: Optional[str] = None,
    ) -> WatchlistYoutubeFeedResponse:
        # 1. 키워드 결정
        has_watchlist = False
        if account_id is not None:
            watchlist = await self._watchlist_port.find_all_by_account(account_id)
            if watchlist:
                has_watchlist = True
                keywords = [item.stock_name for item in watchlist]
            else:
                keywords = _DEFAULT_KEYWORDS
        else:
            keywords = _DEFAULT_KEYWORDS

        # 2. 키워드별 병렬 YouTube 검색
        tasks = [self._search_port.search(keyword=kw) for kw in keywords]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 결과 수집 — video_url 기준 중복 제거
        seen: set[str] = set()
        all_items: list[FeedVideoItem] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            videos, _, _, _ = result
            for v in videos:
                if v.video_url not in seen:
                    seen.add(v.video_url)
                    all_items.append(
                        FeedVideoItem(
                            video_id=_extract_video_id(v.video_url),
                            title=v.title,
                            thumbnail_url=v.thumbnail_url,
                            channel_name=v.channel_name,
                            published_at=v.published_at,
                            video_url=v.video_url,
                        )
                    )

        # 4. 최신순 정렬
        all_items.sort(key=lambda x: x.published_at, reverse=True)

        # 5. 페이지네이션 (page_token은 페이지 번호 문자열)
        page = int(page_token) if page_token and page_token.isdigit() else 1
        total = len(all_items)
        start = (page - 1) * PAGE_SIZE
        page_items = all_items[start: start + PAGE_SIZE]
        next_page_token = str(page + 1) if start + PAGE_SIZE < total else None

        return WatchlistYoutubeFeedResponse(
            has_watchlist=has_watchlist,
            watchlist_keywords=keywords,
            items=page_items,
            next_page_token=next_page_token,
            total_results=total,
        )

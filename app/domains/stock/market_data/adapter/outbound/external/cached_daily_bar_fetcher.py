"""DailyBarFetcherPort decorator — DB 우선 조회, miss 시 외부 fallback + write-through.

causality_agent / history_agent / event_impact 계산 모두 동일한 fetcher 인터페이스로
일봉을 가져올 수 있도록 캐시 레이어 통일.
"""
import logging
from datetime import date, timedelta
from typing import List, Optional

from app.domains.stock.market_data.application.port.out.daily_bar_fetcher_port import (
    DailyBarFetcherPort,
)
from app.domains.stock.market_data.application.port.out.daily_bar_repository_port import (
    DailyBarRepositoryPort,
)
from app.domains.stock.market_data.domain.entity.daily_bar import DailyBar

logger = logging.getLogger(__name__)


def _resolve_range(
    start: Optional[date], end: Optional[date], period: Optional[str]
) -> tuple[Optional[date], Optional[date]]:
    """period 문자열을 (start, end) 윈도우로 변환. 명시 start/end 우선."""
    if start is not None and end is not None:
        return start, end
    if period is None:
        return None, None

    today = date.today()
    p = period.lower()
    if p in {"max", "10y"}:
        return None, today
    if p == "1d":
        return today - timedelta(days=2), today
    if p == "5d":
        return today - timedelta(days=8), today
    if p in {"1mo", "1m"}:
        return today - timedelta(days=35), today
    if p in {"3mo", "3m"}:
        return today - timedelta(days=100), today
    if p in {"6mo", "6m"}:
        return today - timedelta(days=190), today
    if p in {"1y", "12mo"}:
        return today - timedelta(days=380), today
    if p == "2y":
        return today - timedelta(days=760), today
    if p == "5y":
        return today - timedelta(days=1880), today
    return None, today


def _covers(rows: List[DailyBar], start: date, end: date) -> bool:
    """rows 가 (start, end) 거래일 범위를 충분히 커버하는지 휴리스틱.

    엄밀한 거래일 캘린더 비교 대신 'min ≤ start + 7d 이고 max ≥ end - 7d' 만 보장.
    매일 KST 07:30 적재 잡 뒤로 운영되므로 최신성은 자동으로 채워진다.
    """
    if not rows:
        return False
    bar_dates = [r.bar_date for r in rows]
    min_date = min(bar_dates)
    max_date = max(bar_dates)
    return (
        min_date <= start + timedelta(days=7)
        and max_date >= end - timedelta(days=7)
    )


class CachedDailyBarFetcher(DailyBarFetcherPort):

    def __init__(
        self,
        repository: DailyBarRepositoryPort,
        fallback: DailyBarFetcherPort,
    ):
        self._repo = repository
        self._fallback = fallback

    async def fetch(
        self,
        ticker: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        period: Optional[str] = None,
    ) -> List[DailyBar]:
        resolved_start, resolved_end = _resolve_range(start, end, period)

        if resolved_start is not None and resolved_end is not None:
            cached = await self._repo.find_range(ticker, resolved_start, resolved_end)
            if _covers(cached, resolved_start, resolved_end):
                logger.debug(
                    "[CachedDailyBars] DB hit: ticker=%s rows=%d range=%s..%s",
                    ticker, len(cached), resolved_start, resolved_end,
                )
                return cached

        logger.info(
            "[CachedDailyBars] DB miss → fallback fetch: ticker=%s range=%s..%s period=%s",
            ticker, resolved_start, resolved_end, period,
        )
        fresh = await self._fallback.fetch(
            ticker=ticker, start=start, end=end, period=period
        )
        if fresh:
            try:
                await self._repo.upsert_bulk(fresh)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[CachedDailyBars] write-through 실패 (graceful): ticker=%s err=%s",
                    ticker, exc,
                )
        return fresh

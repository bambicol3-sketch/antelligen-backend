"""CachedDailyBarFetcher — DB hit / miss + write-through 검증."""
import asyncio
from datetime import date, timedelta
from typing import List, Optional

from app.domains.stock.market_data.adapter.outbound.external.cached_daily_bar_fetcher import (
    CachedDailyBarFetcher,
    _resolve_range,
)
from app.domains.stock.market_data.application.port.out.daily_bar_fetcher_port import (
    DailyBarFetcherPort,
)
from app.domains.stock.market_data.application.port.out.daily_bar_repository_port import (
    DailyBarRepositoryPort,
)
from app.domains.stock.market_data.domain.entity.daily_bar import DailyBar


class _StubRepo(DailyBarRepositoryPort):
    def __init__(self, bars: List[DailyBar]):
        self.bars = list(bars)
        self.upserts: List[List[DailyBar]] = []

    async def upsert_bulk(self, bars):
        self.upserts.append(list(bars))
        self.bars.extend(bars)
        return len(bars)

    async def find_range(self, ticker, start, end):
        return [
            b for b in self.bars
            if b.ticker == ticker and start <= b.bar_date <= end
        ]

    async def find_around(self, ticker, event_date, before_days, after_days):
        return []

    async def find_latest_bar_date(self, ticker):
        same = [b.bar_date for b in self.bars if b.ticker == ticker]
        return max(same) if same else None

    async def find_distinct_tickers(self):
        return list({b.ticker for b in self.bars})


class _StubFallback(DailyBarFetcherPort):
    def __init__(self, response: List[DailyBar]):
        self.response = list(response)
        self.calls = 0

    async def fetch(
        self,
        ticker: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        period: Optional[str] = None,
    ) -> List[DailyBar]:
        self.calls += 1
        return list(self.response)


def _make_bar(ticker: str, d: date, close: float = 100.0) -> DailyBar:
    return DailyBar(
        ticker=ticker,
        bar_date=d,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000,
    )


def _bars(ticker: str, start: date, count: int) -> List[DailyBar]:
    return [_make_bar(ticker, start + timedelta(days=i)) for i in range(count)]


def test_db_hit_skips_fallback():
    start = date(2026, 3, 1)
    end = date(2026, 3, 31)
    cached = _bars("AAPL", start, 31)
    repo = _StubRepo(cached)
    fallback = _StubFallback([])
    fetcher = CachedDailyBarFetcher(repository=repo, fallback=fallback)

    result = asyncio.run(fetcher.fetch("AAPL", start=start, end=end))

    assert len(result) == 31
    assert fallback.calls == 0
    assert repo.upserts == []


def test_db_miss_invokes_fallback_and_writes_through():
    start = date(2026, 3, 1)
    end = date(2026, 3, 31)
    repo = _StubRepo([])
    fresh = _bars("AAPL", start, 31)
    fallback = _StubFallback(fresh)
    fetcher = CachedDailyBarFetcher(repository=repo, fallback=fallback)

    result = asyncio.run(fetcher.fetch("AAPL", start=start, end=end))

    assert len(result) == 31
    assert fallback.calls == 1
    assert len(repo.upserts) == 1
    assert len(repo.upserts[0]) == 31


def test_partial_db_coverage_falls_back():
    """DB 가 윈도우 일부만 가지고 있으면 fallback 으로 보완."""
    start = date(2026, 3, 1)
    end = date(2026, 3, 31)
    repo = _StubRepo(_bars("AAPL", start, 5))  # 부분 적재
    fallback = _StubFallback(_bars("AAPL", start, 31))
    fetcher = CachedDailyBarFetcher(repository=repo, fallback=fallback)

    result = asyncio.run(fetcher.fetch("AAPL", start=start, end=end))

    assert fallback.calls == 1
    assert len(result) == 31


def test_period_argument_resolves_range():
    today = date.today()
    repo = _StubRepo(_bars("AAPL", today - timedelta(days=400), 400))
    fallback = _StubFallback([])
    fetcher = CachedDailyBarFetcher(repository=repo, fallback=fallback)

    result = asyncio.run(fetcher.fetch("AAPL", period="1y"))

    assert len(result) > 0
    assert fallback.calls == 0


def test_resolve_range_period_aliases():
    today = date.today()
    s, e = _resolve_range(start=None, end=None, period="5d")
    assert e == today
    assert s is not None and (today - s).days <= 8
    s2, e2 = _resolve_range(start=None, end=None, period="max")
    assert s2 is None
    assert e2 == today


def test_explicit_range_overrides_period():
    """start/end 가 명시되면 period 는 무시."""
    explicit_start = date(2026, 1, 1)
    explicit_end = date(2026, 1, 5)
    s, e = _resolve_range(explicit_start, explicit_end, "max")
    assert s == explicit_start
    assert e == explicit_end


def test_fallback_returns_empty_no_writethrough():
    start = date(2026, 3, 1)
    end = date(2026, 3, 31)
    repo = _StubRepo([])
    fallback = _StubFallback([])
    fetcher = CachedDailyBarFetcher(repository=repo, fallback=fallback)

    result = asyncio.run(fetcher.fetch("AAPL", start=start, end=end))

    assert result == []
    assert fallback.calls == 1
    assert repo.upserts == []

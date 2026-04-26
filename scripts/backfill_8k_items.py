"""KR A.1 — TOP20 ticker SEC 8-K items_str 백필 스크립트.

기존 DB의 event_enrichments 행에는 items_str이 NULL이다(0003 마이그레이션 후 컬럼만 추가).
이 스크립트는 SEC EDGAR를 재호출해 items_str을 채워 빈도 분석을 가능하게 한다.

실행:
    python scripts/backfill_8k_items.py [--limit-days 365]

주의:
- SEC fair-use rate limit (10 req/s)에 맞춰 ticker간 2초 sleep.
- 1회 실행에 약 5분 소요 예상.
- 429 응답 발생 시 60초 backoff 후 재시도 (sec_edgar_announcement_client 내장).
"""
import argparse
import asyncio
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# 프로젝트 루트를 import path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.dashboard.adapter.outbound.external.sec_edgar_announcement_client import (
    SecEdgarAnnouncementClient,
)
from app.domains.history_agent.domain.entity.event_enrichment import compute_detail_hash
from app.domains.history_agent.infrastructure.orm.event_enrichment_orm import EventEnrichmentOrm
from app.infrastructure.database.database import AsyncSessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("backfill_8k_items")

# KR A.1 빈도 분석 대상 — 미국 대형주 위주.
TOP20_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
    "JPM", "V", "JNJ", "WMT", "PG", "UNH", "MA", "HD", "DIS", "BAC",
    "XOM", "PFE",
]


async def backfill_ticker(
    client: SecEdgarAnnouncementClient,
    session: AsyncSession,
    ticker: str,
    start_date: date,
    end_date: date,
) -> int:
    """ticker의 8-K filings를 재호출하여 items_str을 채운다.
    Returns: 업데이트된 행 수.
    """
    try:
        events = await client.fetch_announcements(ticker, start_date, end_date)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[%s] SEC fetch 실패: %s", ticker, exc)
        return 0

    updated = 0
    for ev in events:
        if not ev.items_str:
            continue
        # detail_hash는 title 기반이 아닌 detail 기반 — 8-K detail은 본문 요약이지만 backfill은
        # title만 들어오므로 매칭 키를 (ticker, date, type, title) 기준으로 검색.
        # 실제로는 history_agent_usecase가 _from_announcements 시 detail=e.title로 저장하므로
        # detail_hash는 title을 hash한 값. 여기서도 동일하게 계산.
        detail_hash = compute_detail_hash(ev.title)
        stmt = (
            update(EventEnrichmentOrm)
            .where(
                EventEnrichmentOrm.ticker == ticker,
                EventEnrichmentOrm.event_date == ev.date,
                EventEnrichmentOrm.event_type == ev.type.value,
                EventEnrichmentOrm.detail_hash == detail_hash,
                EventEnrichmentOrm.items_str.is_(None),
            )
            .values(items_str=ev.items_str)
        )
        result = await session.execute(stmt)
        updated += result.rowcount or 0

    await session.commit()
    return updated


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-days", type=int, default=365 * 5,
                        help="조회 기간(일). 기본 5년")
    parser.add_argument("--tickers", nargs="*", default=TOP20_TICKERS,
                        help="대상 ticker 목록")
    args = parser.parse_args()

    end_date = date.today()
    start_date = end_date - timedelta(days=args.limit_days)
    logger.info("백필 범위: %s ~ %s, 종목 %d개", start_date, end_date, len(args.tickers))

    client = SecEdgarAnnouncementClient()

    total_updated = 0
    for i, ticker in enumerate(args.tickers, 1):
        async with AsyncSessionLocal() as session:
            updated = await backfill_ticker(client, session, ticker, start_date, end_date)
        total_updated += updated
        logger.info("[%d/%d] %s — items_str 업데이트 %d건",
                    i, len(args.tickers), ticker, updated)
        # SEC fair-use 보호용 ticker간 sleep
        await asyncio.sleep(2)

    logger.info("완료. 총 %d건 업데이트", total_updated)
    logger.info("\n빈도 분석 SQL:\n"
                "  SELECT items_str, event_type, COUNT(*) AS rows\n"
                "  FROM event_enrichments\n"
                "  WHERE event_type = 'MAJOR_EVENT' AND items_str IS NOT NULL\n"
                "  GROUP BY items_str, event_type\n"
                "  ORDER BY rows DESC LIMIT 20;")


if __name__ == "__main__":
    asyncio.run(main())

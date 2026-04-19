import asyncio
import json
import logging
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.dashboard.adapter.outbound.external.dart_announcement_client import (
    DartAnnouncementClient,
)
from app.domains.dashboard.adapter.outbound.external.dart_corporate_event_client import (
    DartCorporateEventClient,
)
from app.domains.dashboard.adapter.outbound.external.sec_edgar_announcement_client import (
    SecEdgarAnnouncementClient,
)
from app.domains.dashboard.adapter.outbound.external.yahoo_finance_asset_type_client import (
    YahooFinanceAssetTypeClient,
)
from app.domains.dashboard.adapter.outbound.external.yahoo_finance_corporate_event_client import (
    YahooFinanceCorporateEventClient,
)
from app.domains.dashboard.adapter.outbound.external.yahoo_finance_stock_client import (
    YahooFinanceStockClient,
)
from app.domains.history_agent.adapter.outbound.persistence.event_enrichment_repository_impl import (
    EventEnrichmentRepositoryImpl,
)
from app.domains.history_agent.application.response.timeline_response import TimelineResponse
from app.domains.history_agent.application.usecase.history_agent_usecase import HistoryAgentUseCase
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.database.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history-agent", tags=["HistoryAgent"])

_VALID_PERIODS = {"1D", "1W", "1M", "1Y"}


async def _resolve_corp_code(ticker: str, db: AsyncSession) -> Optional[str]:
    if not (ticker.isdigit() and len(ticker) == 6):
        return None
    from app.domains.disclosure.adapter.outbound.persistence.company_repository_impl import (
        CompanyRepositoryImpl,
    )
    company = await CompanyRepositoryImpl(db).find_by_stock_code(ticker)
    return company.corp_code if company else None


@router.get("/timeline", response_model=BaseResponse[TimelineResponse])
async def get_timeline(
    ticker: str = Query(..., description="종목 코드 (예: AAPL, 005930)"),
    period: str = Query("1Y", description="조회 기간: 1D | 1W | 1M | 1Y"),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """가격·기업·공시 이벤트를 날짜순으로 통합한 타임라인을 반환합니다.

    - PRICE: 52주 신고가/신저가, 급등락, 거래량 급증, 갭
    - CORPORATE: 실적, 배당, 유상증자, 자사주, 임원변동
    - ANNOUNCEMENT: 합병/인수/계약 공시 (DART or SEC EDGAR)
    """
    if period not in _VALID_PERIODS:
        raise AppException(
            status_code=400,
            message=f"유효하지 않은 period입니다. 사용 가능: {', '.join(sorted(_VALID_PERIODS))}",
        )

    ticker = ticker.upper()
    corp_code = await _resolve_corp_code(ticker, db)

    result = await HistoryAgentUseCase(
        stock_bars_port=YahooFinanceStockClient(),
        yfinance_corporate_port=YahooFinanceCorporateEventClient(),
        dart_corporate_client=DartCorporateEventClient(),
        sec_edgar_port=SecEdgarAnnouncementClient(),
        dart_announcement_client=DartAnnouncementClient(),
        redis=redis,
        enrichment_repo=EventEnrichmentRepositoryImpl(db),
        asset_type_port=YahooFinanceAssetTypeClient(),
    ).execute(ticker=ticker, period=period, corp_code=corp_code)

    return BaseResponse.ok(data=result)


@router.get("/timeline/stream")
async def stream_timeline(
    ticker: str = Query(..., description="종목 코드 (예: AAPL, 005930)"),
    period: str = Query("1Y", description="조회 기간: 1D | 1W | 1M | 1Y"),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """타임라인 데이터를 SSE로 스트리밍합니다. progress / done / error 이벤트를 순서대로 전송합니다."""
    if period not in _VALID_PERIODS:
        raise AppException(
            status_code=400,
            message=f"유효하지 않은 period입니다. 사용 가능: {', '.join(sorted(_VALID_PERIODS))}",
        )

    ticker = ticker.upper()
    corp_code = await _resolve_corp_code(ticker, db)

    queue: asyncio.Queue = asyncio.Queue()

    async def on_progress(step: str, label: str, pct: int) -> None:
        await queue.put({"type": "progress", "step": step, "label": label, "pct": pct})

    usecase = HistoryAgentUseCase(
        stock_bars_port=YahooFinanceStockClient(),
        yfinance_corporate_port=YahooFinanceCorporateEventClient(),
        dart_corporate_client=DartCorporateEventClient(),
        sec_edgar_port=SecEdgarAnnouncementClient(),
        dart_announcement_client=DartAnnouncementClient(),
        redis=redis,
        enrichment_repo=EventEnrichmentRepositoryImpl(db),
        asset_type_port=YahooFinanceAssetTypeClient(),
    )

    async def _run() -> None:
        try:
            result = await usecase.execute(
                ticker=ticker,
                period=period,
                corp_code=corp_code,
                on_progress=on_progress,
            )
            await queue.put({"type": "done", "data": result.model_dump_json()})
        except Exception as exc:
            logger.error("[stream_timeline] 오류: %s", exc)
            await queue.put({"type": "error", "message": "타임라인 데이터 처리 중 오류가 발생했습니다."})

    asyncio.create_task(_run())

    async def _event_generator():
        while True:
            item = await queue.get()
            if item["type"] == "progress":
                data = json.dumps({"step": item["step"], "label": item["label"], "pct": item["pct"]})
                yield f"event: progress\ndata: {data}\n\n"
            elif item["type"] == "done":
                yield f"event: done\ndata: {item['data']}\n\n"
                break
            elif item["type"] == "error":
                data = json.dumps({"message": item["message"]})
                yield f"event: error\ndata: {data}\n\n"
                break

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

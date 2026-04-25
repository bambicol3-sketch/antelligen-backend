import logging
from datetime import date

import redis.asyncio as aioredis

from app.domains.smart_money.application.port.out.investor_flow_repository_port import InvestorFlowRepositoryPort
from app.domains.smart_money.application.response.investor_flow_trend_response import (
    InvestorFlowTrendPoint,
    InvestorFlowTrendResponse,
)
from app.domains.smart_money.domain.entity.investor_flow import InvestorType

logger = logging.getLogger(__name__)

_CACHE_TTL = 600  # 10분


class GetInvestorFlowTrendUseCase:

    def __init__(self, repository: InvestorFlowRepositoryPort, redis: aioredis.Redis):
        self._repository = repository
        self._redis = redis

    async def execute(
        self, stock_code: str, since_date: date, days: int
    ) -> InvestorFlowTrendResponse:
        cache_key = f"smart_money:trend:{stock_code}:{since_date}:{days}"

        cached = await self._redis.get(cache_key)
        if cached:
            try:
                logger.info("[trend] 캐시 히트: %s days=%d", stock_code, days)
                return InvestorFlowTrendResponse.model_validate_json(cached)
            except Exception:
                pass

        flows = await self._repository.find_trend_by_stock(stock_code, since_date)

        # 날짜별로 투자자 유형 집계
        daily: dict[date, dict[str, int]] = {}
        stock_name: str | None = None

        for f in flows:
            if stock_name is None:
                stock_name = f.stock_name
            day_data = daily.setdefault(f.date, {"FOREIGN": 0, "INSTITUTION": 0, "INDIVIDUAL": 0})
            day_data[f.investor_type.value] = f.net_buy_amount

        points = [
            InvestorFlowTrendPoint(
                date=d,
                foreign=daily[d].get(InvestorType.FOREIGN.value, 0),
                institution=daily[d].get(InvestorType.INSTITUTION.value, 0),
                individual=daily[d].get(InvestorType.INDIVIDUAL.value, 0),
            )
            for d in sorted(daily)
        ]

        response = InvestorFlowTrendResponse(
            stock_code=stock_code,
            stock_name=stock_name,
            since_date=since_date,
            days=days,
            points=points,
        )

        await self._redis.setex(cache_key, _CACHE_TTL, response.model_dump_json())
        logger.info("[trend] %s — %d일치 %d포인트 반환", stock_code, days, len(points))

        return response

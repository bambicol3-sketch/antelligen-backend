import logging

from app.domains.smart_money.application.port.out.investor_flow_repository_port import InvestorFlowRepositoryPort
from app.domains.smart_money.application.response.concentrated_buying_response import (
    ConcentratedBuyingItem,
    ConcentratedBuyingResponse,
)
from app.domains.smart_money.domain.entity.investor_flow import InvestorType
from app.domains.smart_money.domain.service.smart_money_domain_service import SmartMoneyDomainService

logger = logging.getLogger(__name__)


class GetConcentratedBuyingUseCase:

    def __init__(self, repository: InvestorFlowRepositoryPort):
        self._repository = repository

    async def execute(self, days: int = 5, limit: int = 50) -> ConcentratedBuyingResponse:
        # 1. 최근 N 영업일 날짜 조회 (외국인 기준 — 외국인·기관 동일 날짜에 수집됨)
        recent_dates = await self._repository.find_recent_dates(
            InvestorType.FOREIGN.value, days
        )
        if not recent_dates:
            logger.warning("[concentrated] 수집된 investor_flow 데이터 없음")
            return ConcentratedBuyingResponse(
                since_date=None,  # type: ignore[arg-type]
                days=days,
                total=0,
                items=[],
            )

        since_date = min(recent_dates)

        # 2. 외국인·기관 N일 누적 순매수 집계
        foreign_flows = await self._repository.find_accumulated_flows(
            since_date, InvestorType.FOREIGN.value
        )
        institution_flows = await self._repository.find_accumulated_flows(
            since_date, InvestorType.INSTITUTION.value
        )

        # 3. 도메인 서비스 — 교집합 + 집중 매수 점수 산출
        concentrated = SmartMoneyDomainService.compute_concentrated_stocks(
            foreign_flows=foreign_flows,
            institution_flows=institution_flows,
            limit=limit,
        )

        items = [
            ConcentratedBuyingItem(
                stock_code=s.stock_code,
                stock_name=s.stock_name,
                foreign_net_buy=s.foreign_net_buy,
                institution_net_buy=s.institution_net_buy,
                total_net_buy=s.total_net_buy,
                concentration_score=s.concentration_score,
            )
            for s in concentrated
        ]

        logger.info(
            "[concentrated] days=%d, since=%s, 교집합 %d종목",
            days, since_date, len(items),
        )

        return ConcentratedBuyingResponse(
            since_date=since_date,
            days=days,
            total=len(items),
            items=items,
        )

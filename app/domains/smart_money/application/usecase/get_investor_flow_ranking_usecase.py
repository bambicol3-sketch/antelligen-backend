from datetime import date

from app.domains.smart_money.application.port.out.investor_flow_repository_port import InvestorFlowRepositoryPort
from app.domains.smart_money.application.response.investor_flow_ranking_response import (
    InvestorFlowRankingItem,
    InvestorFlowRankingResponse,
)
from app.domains.smart_money.domain.entity.investor_flow import InvestorType


class GetInvestorFlowRankingUseCase:

    def __init__(self, repository: InvestorFlowRepositoryPort):
        self._repository = repository

    async def execute(
        self,
        investor_type: InvestorType,
        target_date: date | None = None,
        limit: int = 20,
    ) -> InvestorFlowRankingResponse:
        if target_date is None:
            target_date = await self._repository.find_latest_date(investor_type.value)

        flows = []
        if target_date is not None:
            flows = await self._repository.find_ranking(target_date, investor_type.value, limit)

        items = [
            InvestorFlowRankingItem(
                rank=idx + 1,
                stock_code=f.stock_code,
                stock_name=f.stock_name,
                net_buy_amount=f.net_buy_amount,
                net_buy_volume=f.net_buy_volume,
            )
            for idx, f in enumerate(flows)
        ]

        return InvestorFlowRankingResponse(
            investor_type=investor_type,
            date=target_date,
            items=items,
        )

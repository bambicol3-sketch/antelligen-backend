from app.domains.smart_money.application.port.out.global_portfolio_repository_port import GlobalPortfolioRepositoryPort
from app.domains.smart_money.application.response.global_portfolio_response import (
    GlobalPortfolioItem,
    GlobalPortfolioResponse,
    InvestorListResponse,
)
from app.domains.smart_money.domain.entity.global_portfolio import ChangeType


class GetGlobalPortfolioUseCase:

    def __init__(self, repository: GlobalPortfolioRepositoryPort):
        self._repository = repository

    async def execute(
        self,
        investor_name: str | None = None,
        change_type: ChangeType | None = None,
    ) -> GlobalPortfolioResponse:
        holdings = await self._repository.find_latest(
            investor_name=investor_name,
            change_type=change_type,
        )

        items = [
            GlobalPortfolioItem(
                investor_name=h.investor_name,
                ticker=h.ticker,
                stock_name=h.stock_name,
                shares=h.shares,
                market_value=h.market_value,
                portfolio_weight=h.portfolio_weight,
                change_type=h.change_type,
                reported_at=h.reported_at,
            )
            for h in holdings
        ]

        return GlobalPortfolioResponse(
            investor_name=investor_name,
            change_type=change_type,
            total=len(items),
            items=items,
        )

    async def get_investor_names(self) -> InvestorListResponse:
        names = await self._repository.find_investor_names()
        return InvestorListResponse(investors=names)

from app.domains.smart_money.application.port.out.kr_portfolio_repository_port import KrPortfolioRepositoryPort
from app.domains.smart_money.application.response.kr_portfolio_response import KrPortfolioItem, KrPortfolioResponse


class GetKrPortfolioUseCase:

    def __init__(self, repository: KrPortfolioRepositoryPort):
        self._repository = repository

    async def execute(self, investor_name: str) -> KrPortfolioResponse:
        holdings = await self._repository.find_by_investor(investor_name)
        items = [
            KrPortfolioItem(
                investor_name=h.investor_name,
                investor_type=h.investor_type,
                stock_code=h.stock_code,
                stock_name=h.stock_name,
                shares_held=h.shares_held,
                ownership_ratio=h.ownership_ratio,
                change_type=h.change_type,
                reported_at=h.reported_at,
            )
            for h in holdings
        ]
        return KrPortfolioResponse(
            investor_name=investor_name,
            items=items,
            total=len(items),
        )

    async def get_total_count(self) -> int:
        return await self._repository.count()

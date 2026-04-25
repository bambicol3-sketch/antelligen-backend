from app.domains.smart_money.application.port.out.global_portfolio_repository_port import GlobalPortfolioRepositoryPort
from app.domains.smart_money.application.response.us_concentrated_buying_response import (
    USConcentratedBuyingItem,
    USConcentratedBuyingResponse,
)


class GetUSConcentratedBuyingUseCase:

    def __init__(self, repository: GlobalPortfolioRepositoryPort):
        self._repository = repository

    async def execute(self, limit: int = 20) -> USConcentratedBuyingResponse:
        stocks = await self._repository.find_us_concentrated(limit=limit)
        items = [
            USConcentratedBuyingItem(
                ticker=stock.ticker,
                stock_name=stock.stock_name,
                investor_count=stock.investor_count,
                total_market_value=stock.total_market_value,
                investors=stock.investors,
                reported_at=stock.reported_at,
            )
            for stock in stocks
        ]
        return USConcentratedBuyingResponse(items=items, total=len(items))

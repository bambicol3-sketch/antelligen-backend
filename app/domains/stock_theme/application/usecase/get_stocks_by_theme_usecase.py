from app.domains.stock_theme.application.port.out.stock_theme_repository_port import StockThemeRepositoryPort
from app.domains.stock_theme.application.response.stocks_by_theme_response import (
    StocksByThemeGroupedResponse,
    StocksByThemeListResponse,
    ThemeGroupResponse,
    ThemeStockItem,
)
from app.domains.stock_theme.domain.value_object.theme_name import MAIN_THEMES


class GetStocksByThemeUseCase:
    def __init__(self, repository: StockThemeRepositoryPort):
        self._repository = repository

    async def get_all_grouped(self) -> StocksByThemeGroupedResponse:
        all_stocks = await self._repository.find_all()
        theme_map: dict[str, list[ThemeStockItem]] = {t: [] for t in MAIN_THEMES}

        for stock in all_stocks:
            for theme in stock.themes:
                if theme in theme_map:
                    theme_map[theme].append(
                        ThemeStockItem(code=stock.code, name=stock.name, theme_name=theme)
                    )

        return StocksByThemeGroupedResponse(
            themes=[
                ThemeGroupResponse(theme_name=t, stocks=stocks)
                for t, stocks in theme_map.items()
                if stocks
            ]
        )

    async def get_by_theme(self, theme_name: str) -> StocksByThemeListResponse:
        stocks = await self._repository.find_all_by_theme(theme_name)
        items = [
            ThemeStockItem(code=s.code, name=s.name, theme_name=theme_name)
            for s in stocks
        ]
        return StocksByThemeListResponse(
            theme_name=theme_name,
            total=len(items),
            stocks=items,
        )

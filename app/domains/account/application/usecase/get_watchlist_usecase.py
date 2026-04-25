from app.domains.account.application.port.out.watchlist_repository_port import WatchlistRepositoryPort
from app.domains.account.application.response.watchlist_response import GetWatchlistResponse, WatchlistItemWithTheme


class GetWatchlistUseCase:
    def __init__(self, watchlist_port: WatchlistRepositoryPort):
        self._watchlist_port = watchlist_port

    async def execute(self, account_id: int) -> GetWatchlistResponse:
        items = await self._watchlist_port.find_all_with_theme_by_account(account_id)
        return GetWatchlistResponse(
            stocks=[
                WatchlistItemWithTheme(
                    stock_code=i.stock_code,
                    stock_name=i.stock_name,
                    theme_name=i.theme_name,
                )
                for i in items
            ]
        )

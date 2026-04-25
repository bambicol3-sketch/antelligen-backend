from app.common.exception.app_exception import AppException
from app.domains.account.application.exception.watchlist_exceptions import WatchlistStockNotFoundException
from app.domains.account.application.port.out.watchlist_repository_port import WatchlistRepositoryPort


class RemoveWatchlistStockUseCase:
    def __init__(self, watchlist_port: WatchlistRepositoryPort):
        self._watchlist_port = watchlist_port

    async def execute(self, account_id: int, stock_code: str) -> None:
        if not await self._watchlist_port.exists(account_id, stock_code):
            if await self._watchlist_port.exists_for_any_user(stock_code):
                raise AppException(status_code=403, message="다른 사용자의 관심종목입니다.")
            raise WatchlistStockNotFoundException(stock_code)

        await self._watchlist_port.remove(account_id, stock_code)

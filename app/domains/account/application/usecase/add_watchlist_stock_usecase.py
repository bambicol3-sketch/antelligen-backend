from app.common.exception.app_exception import AppException
from app.domains.account.application.exception.watchlist_exceptions import DuplicateWatchlistStockException
from app.domains.account.application.port.out.stock_master_port import StockMasterPort
from app.domains.account.application.port.out.watchlist_repository_port import WatchlistRepositoryPort
from app.domains.account.application.response.watchlist_response import WatchlistResponse, WatchlistStockItem


class AddWatchlistStockUseCase:
    def __init__(
        self,
        watchlist_port: WatchlistRepositoryPort,
        stock_master_port: StockMasterPort,
    ):
        self._watchlist_port = watchlist_port
        self._stock_master_port = stock_master_port

    async def execute(self, account_id: int, stock_code: str) -> WatchlistResponse:
        found = await self._stock_master_port.find_by_codes([stock_code])
        if not found:
            raise AppException(status_code=404, message=f"존재하지 않는 종목 코드입니다: {stock_code}")

        if await self._watchlist_port.exists(account_id, stock_code):
            raise DuplicateWatchlistStockException(stock_code)

        await self._watchlist_port.add(account_id, found[0])

        all_items = await self._watchlist_port.find_all_by_account(account_id)
        return WatchlistResponse(
            stocks=[WatchlistStockItem(code=i.stock_code, name=i.stock_name) for i in all_items]
        )

from app.common.exception.app_exception import AppException
from app.domains.account.application.exception.watchlist_exceptions import (
    DuplicateWatchlistStockException,
    WatchlistStockNotFoundException,
)
from app.domains.account.application.port.out.stock_master_port import StockMasterPort
from app.domains.account.application.port.out.watchlist_repository_port import WatchlistRepositoryPort
from app.domains.account.application.response.watchlist_response import GetWatchlistResponse, WatchlistItemWithTheme


class UpdateWatchlistStockUseCase:
    def __init__(
        self,
        watchlist_port: WatchlistRepositoryPort,
        stock_master_port: StockMasterPort,
    ):
        self._watchlist_port = watchlist_port
        self._stock_master_port = stock_master_port

    async def execute(self, account_id: int, old_stock_code: str, new_stock_code: str) -> GetWatchlistResponse:
        # 1. 기존 종목이 watchlist에 존재하는지 확인
        if not await self._watchlist_port.exists(account_id, old_stock_code):
            raise WatchlistStockNotFoundException(old_stock_code)

        # 2. 교체할 새 종목이 stock master에 존재하는지 확인
        found = await self._stock_master_port.find_by_codes([new_stock_code])
        if not found:
            raise AppException(status_code=404, message=f"존재하지 않는 종목 코드입니다: {new_stock_code}")

        # 3. 새 종목이 이미 watchlist에 있는지 확인
        if await self._watchlist_port.exists(account_id, new_stock_code):
            raise DuplicateWatchlistStockException(new_stock_code)

        # 4. 원자적 교체
        await self._watchlist_port.replace(account_id, old_stock_code, found[0])

        # 5. 변경된 전체 watchlist 반환
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

from abc import ABC, abstractmethod

from app.domains.account.domain.entity.watchlist_item import WatchlistItem


class StockMasterPort(ABC):

    @abstractmethod
    async def find_by_codes(self, codes: list[str]) -> list[WatchlistItem]:
        """주어진 코드 목록 중 존재하는 종목만 반환한다."""
        pass

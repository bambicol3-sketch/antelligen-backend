from abc import ABC, abstractmethod

from app.domains.account.domain.entity.watchlist_item import WatchlistItem


class WatchlistSavePort(ABC):

    @abstractmethod
    async def save_all(self, account_id: int, items: list[WatchlistItem]) -> list[WatchlistItem]:
        pass

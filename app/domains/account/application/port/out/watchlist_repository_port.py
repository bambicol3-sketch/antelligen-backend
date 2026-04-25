from abc import ABC, abstractmethod

from app.domains.account.domain.entity.watchlist_item import WatchlistItem
from app.domains.account.domain.entity.watchlist_with_theme_item import WatchlistWithThemeItem


class WatchlistRepositoryPort(ABC):

    @abstractmethod
    async def add(self, account_id: int, item: WatchlistItem) -> None:
        pass

    @abstractmethod
    async def find_all_by_account(self, account_id: int) -> list[WatchlistItem]:
        pass

    @abstractmethod
    async def find_all_with_theme_by_account(self, account_id: int) -> list[WatchlistWithThemeItem]:
        pass

    @abstractmethod
    async def exists(self, account_id: int, stock_code: str) -> bool:
        pass

    @abstractmethod
    async def exists_for_any_user(self, stock_code: str) -> bool:
        pass

    @abstractmethod
    async def remove(self, account_id: int, stock_code: str) -> None:
        pass

    @abstractmethod
    async def replace(self, account_id: int, old_code: str, new_item: WatchlistItem) -> None:
        """old_code 항목을 삭제하고 new_item을 추가한다 (atomic)."""
        pass

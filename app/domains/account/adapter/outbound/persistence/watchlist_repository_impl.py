from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.account.application.port.out.watchlist_repository_port import WatchlistRepositoryPort
from app.domains.account.application.port.out.watchlist_save_port import WatchlistSavePort
from app.domains.account.domain.entity.watchlist_item import WatchlistItem
from app.domains.account.domain.entity.watchlist_with_theme_item import WatchlistWithThemeItem
from app.domains.account.infrastructure.orm.user_watchlist_orm import UserWatchlistOrm
from app.domains.stock_theme.domain.value_object.theme_name import MAIN_THEMES
from app.domains.stock_theme.infrastructure.orm.stock_theme_orm import StockThemeOrm


class WatchlistRepositoryImpl(WatchlistSavePort, WatchlistRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    # ── WatchlistSavePort ────────────────────────────────────────────────
    async def save_all(self, account_id: int, items: list[WatchlistItem]) -> list[WatchlistItem]:
        if not items:
            return []
        for item in items:
            self._db.add(
                UserWatchlistOrm(
                    account_id=account_id,
                    stock_code=item.stock_code,
                    stock_name=item.stock_name,
                )
            )
        await self._db.commit()
        return items

    # ── WatchlistRepositoryPort ──────────────────────────────────────────
    async def add(self, account_id: int, item: WatchlistItem) -> None:
        self._db.add(
            UserWatchlistOrm(
                account_id=account_id,
                stock_code=item.stock_code,
                stock_name=item.stock_name,
            )
        )
        await self._db.commit()

    async def find_all_by_account(self, account_id: int) -> list[WatchlistItem]:
        stmt = select(UserWatchlistOrm).where(UserWatchlistOrm.account_id == account_id)
        result = await self._db.execute(stmt)
        return [
            WatchlistItem(stock_code=row.stock_code, stock_name=row.stock_name)
            for row in result.scalars().all()
        ]

    async def find_all_with_theme_by_account(self, account_id: int) -> list[WatchlistWithThemeItem]:
        watchlist_rows = await self.find_all_by_account(account_id)
        if not watchlist_rows:
            return []

        codes = [item.stock_code for item in watchlist_rows]
        theme_stmt = select(StockThemeOrm).where(StockThemeOrm.code.in_(codes))
        theme_result = await self._db.execute(theme_stmt)

        # code → 대표 테마명 (MAIN_THEMES 기준 첫 번째 일치, 없으면 첫 번째 테마)
        theme_map: dict[str, str] = {}
        for row in theme_result.scalars().all():
            if row.code not in theme_map:
                themes: list[str] = row.themes or []
                main = next((t for t in themes if t in MAIN_THEMES), themes[0] if themes else "")
                theme_map[row.code] = main

        return [
            WatchlistWithThemeItem(
                stock_code=item.stock_code,
                stock_name=item.stock_name,
                theme_name=theme_map.get(item.stock_code, ""),
            )
            for item in watchlist_rows
        ]

    async def exists(self, account_id: int, stock_code: str) -> bool:
        stmt = select(UserWatchlistOrm).where(
            UserWatchlistOrm.account_id == account_id,
            UserWatchlistOrm.stock_code == stock_code,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists_for_any_user(self, stock_code: str) -> bool:
        stmt = select(UserWatchlistOrm).where(UserWatchlistOrm.stock_code == stock_code)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def remove(self, account_id: int, stock_code: str) -> None:
        stmt = delete(UserWatchlistOrm).where(
            UserWatchlistOrm.account_id == account_id,
            UserWatchlistOrm.stock_code == stock_code,
        )
        await self._db.execute(stmt)
        await self._db.commit()

    async def replace(self, account_id: int, old_code: str, new_item: WatchlistItem) -> None:
        await self._db.execute(
            delete(UserWatchlistOrm).where(
                UserWatchlistOrm.account_id == account_id,
                UserWatchlistOrm.stock_code == old_code,
            )
        )
        self._db.add(
            UserWatchlistOrm(
                account_id=account_id,
                stock_code=new_item.stock_code,
                stock_name=new_item.stock_name,
            )
        )
        await self._db.commit()

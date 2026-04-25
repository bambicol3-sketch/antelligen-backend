from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.account.application.port.out.stock_master_port import StockMasterPort
from app.domains.account.domain.entity.watchlist_item import WatchlistItem
from app.domains.stock_theme.infrastructure.orm.stock_theme_orm import StockThemeOrm


class StockMasterRepositoryImpl(StockMasterPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_codes(self, codes: list[str]) -> list[WatchlistItem]:
        if not codes:
            return []
        stmt = select(StockThemeOrm).where(StockThemeOrm.code.in_(codes))
        result = await self._db.execute(stmt)
        rows = result.scalars().all()
        # 코드 중복 제거 (name이 unique이지만 code는 중복 가능하므로 첫 번째만 사용)
        seen: set[str] = set()
        items: list[WatchlistItem] = []
        for row in rows:
            if row.code not in seen:
                seen.add(row.code)
                items.append(WatchlistItem(stock_code=row.code, stock_name=row.name))
        return items

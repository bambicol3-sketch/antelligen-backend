from datetime import datetime

from sqlalchemy import select, func, distinct
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.smart_money.application.port.out.kr_portfolio_repository_port import KrPortfolioRepositoryPort
from app.domains.smart_money.domain.entity.kr_portfolio import KrPortfolioHolding
from app.domains.smart_money.infrastructure.mapper.kr_portfolio_mapper import KrPortfolioMapper
from app.domains.smart_money.infrastructure.orm.kr_portfolio_orm import KrPortfolioOrm


class KrPortfolioRepositoryImpl(KrPortfolioRepositoryPort):

    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_investor(self, investor_name: str) -> list[KrPortfolioHolding]:
        stmt = (
            select(KrPortfolioOrm)
            .where(KrPortfolioOrm.investor_name == investor_name)
            .order_by(KrPortfolioOrm.ownership_ratio.desc())
        )
        result = await self._db.execute(stmt)
        return [KrPortfolioMapper.to_entity(row) for row in result.scalars().all()]

    async def find_one(self, investor_name: str, stock_code: str) -> KrPortfolioHolding | None:
        stmt = select(KrPortfolioOrm).where(
            KrPortfolioOrm.investor_name == investor_name,
            KrPortfolioOrm.stock_code == stock_code,
        )
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        return KrPortfolioMapper.to_entity(orm) if orm else None

    async def upsert(self, holding: KrPortfolioHolding) -> None:
        now = datetime.now()
        stmt = pg_insert(KrPortfolioOrm).values(
            investor_name=holding.investor_name,
            investor_type=holding.investor_type,
            stock_code=holding.stock_code,
            stock_name=holding.stock_name,
            shares_held=holding.shares_held,
            ownership_ratio=holding.ownership_ratio,
            change_type=holding.change_type,
            reported_at=holding.reported_at,
            collected_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_kr_portfolio",
            set_={
                "investor_type": stmt.excluded.investor_type,
                "stock_name": stmt.excluded.stock_name,
                "shares_held": stmt.excluded.shares_held,
                "ownership_ratio": stmt.excluded.ownership_ratio,
                "change_type": stmt.excluded.change_type,
                "reported_at": stmt.excluded.reported_at,
                "collected_at": stmt.excluded.collected_at,
            },
        )
        await self._db.execute(stmt)
        await self._db.commit()

    async def find_all_investor_names(self) -> list[str]:
        stmt = select(distinct(KrPortfolioOrm.investor_name)).order_by(KrPortfolioOrm.investor_name)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        stmt = select(func.count()).select_from(KrPortfolioOrm)
        result = await self._db.execute(stmt)
        return result.scalar_one()

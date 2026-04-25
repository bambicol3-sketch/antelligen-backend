from datetime import date

from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.smart_money.application.port.out.global_portfolio_repository_port import GlobalPortfolioRepositoryPort
from app.domains.smart_money.domain.entity.global_portfolio import ChangeType, GlobalPortfolio
from app.domains.smart_money.infrastructure.mapper.global_portfolio_mapper import GlobalPortfolioMapper
from app.domains.smart_money.infrastructure.orm.global_portfolio_orm import GlobalPortfolioOrm


class GlobalPortfolioRepositoryImpl(GlobalPortfolioRepositoryPort):

    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_previous_holdings(
        self, investor_name: str, before_date: date
    ) -> list[GlobalPortfolio]:
        # 지정 날짜 이전 가장 최근 reported_at 조회
        subq = (
            select(func.max(GlobalPortfolioOrm.reported_at))
            .where(
                GlobalPortfolioOrm.investor_name == investor_name,
                GlobalPortfolioOrm.reported_at < before_date,
            )
            .scalar_subquery()
        )
        stmt = select(GlobalPortfolioOrm).where(
            GlobalPortfolioOrm.investor_name == investor_name,
            GlobalPortfolioOrm.reported_at == subq,
        )
        result = await self._db.execute(stmt)
        return [GlobalPortfolioMapper.to_entity(orm) for orm in result.scalars().all()]

    async def exists_for_period(self, investor_name: str, reported_at: date) -> bool:
        stmt = select(GlobalPortfolioOrm.id).where(
            GlobalPortfolioOrm.investor_name == investor_name,
            GlobalPortfolioOrm.reported_at == reported_at,
        ).limit(1)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def save_batch(self, portfolios: list[GlobalPortfolio]) -> int:
        if not portfolios:
            return 0
        orm_list = [GlobalPortfolioMapper.to_orm(p) for p in portfolios]
        self._db.add_all(orm_list)
        await self._db.commit()
        return len(orm_list)

    async def find_latest(
        self,
        investor_name: str | None = None,
        change_type: ChangeType | None = None,
    ) -> list[GlobalPortfolio]:
        # 투자자별 최신 reported_at 서브쿼리
        if investor_name:
            latest_date_subq = (
                select(func.max(GlobalPortfolioOrm.reported_at))
                .where(GlobalPortfolioOrm.investor_name == investor_name)
                .scalar_subquery()
            )
            conditions = [
                GlobalPortfolioOrm.investor_name == investor_name,
                GlobalPortfolioOrm.reported_at == latest_date_subq,
            ]
        else:
            # 투자자별 최신 날짜를 각각 구해서 조인
            latest_subq = (
                select(
                    GlobalPortfolioOrm.investor_name,
                    func.max(GlobalPortfolioOrm.reported_at).label("max_date"),
                )
                .group_by(GlobalPortfolioOrm.investor_name)
                .subquery()
            )
            stmt = select(GlobalPortfolioOrm).join(
                latest_subq,
                (GlobalPortfolioOrm.investor_name == latest_subq.c.investor_name)
                & (GlobalPortfolioOrm.reported_at == latest_subq.c.max_date),
            )
            if change_type is not None:
                stmt = stmt.where(GlobalPortfolioOrm.change_type == change_type.value)
            stmt = stmt.order_by(
                GlobalPortfolioOrm.investor_name,
                GlobalPortfolioOrm.portfolio_weight.desc(),
            )
            result = await self._db.execute(stmt)
            return [GlobalPortfolioMapper.to_entity(row) for row in result.scalars().all()]

        if change_type is not None:
            conditions.append(GlobalPortfolioOrm.change_type == change_type.value)

        stmt = (
            select(GlobalPortfolioOrm)
            .where(*conditions)
            .order_by(GlobalPortfolioOrm.portfolio_weight.desc())
        )
        result = await self._db.execute(stmt)
        return [GlobalPortfolioMapper.to_entity(row) for row in result.scalars().all()]

    async def find_investor_names(self) -> list[str]:
        stmt = select(distinct(GlobalPortfolioOrm.investor_name)).order_by(
            GlobalPortfolioOrm.investor_name
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

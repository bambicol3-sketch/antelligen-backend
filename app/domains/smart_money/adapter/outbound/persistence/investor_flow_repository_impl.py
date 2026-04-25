from datetime import date

from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.smart_money.application.port.out.investor_flow_repository_port import InvestorFlowRepositoryPort
from app.domains.smart_money.domain.entity.investor_flow import InvestorFlow
from app.domains.smart_money.domain.service.smart_money_domain_service import AccumulatedFlow
from app.domains.smart_money.infrastructure.mapper.investor_flow_mapper import InvestorFlowMapper
from app.domains.smart_money.infrastructure.orm.investor_flow_orm import InvestorFlowOrm


class InvestorFlowRepositoryImpl(InvestorFlowRepositoryPort):

    def __init__(self, db: AsyncSession):
        self._db = db

    async def exists(self, target_date: date, investor_type: str, stock_code: str) -> bool:
        stmt = select(InvestorFlowOrm.id).where(
            InvestorFlowOrm.date == target_date,
            InvestorFlowOrm.investor_type == investor_type,
            InvestorFlowOrm.stock_code == stock_code,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def save_batch(self, flows: list[InvestorFlow]) -> int:
        if not flows:
            return 0
        orm_list = [InvestorFlowMapper.to_orm(f) for f in flows]
        self._db.add_all(orm_list)
        await self._db.commit()
        return len(orm_list)

    async def find_ranking(
        self, target_date: date, investor_type: str, limit: int
    ) -> list[InvestorFlow]:
        stmt = (
            select(InvestorFlowOrm)
            .where(
                InvestorFlowOrm.date == target_date,
                InvestorFlowOrm.investor_type == investor_type,
            )
            .order_by(InvestorFlowOrm.net_buy_amount.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return [InvestorFlowMapper.to_entity(row) for row in result.scalars().all()]

    async def find_latest_date(self, investor_type: str) -> date | None:
        stmt = select(func.max(InvestorFlowOrm.date)).where(
            InvestorFlowOrm.investor_type == investor_type
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_recent_dates(self, investor_type: str, n: int) -> list[date]:
        # (date, investor_type) 복합 인덱스가 있으면 최적 — 현재 단일 인덱스 사용
        stmt = (
            select(distinct(InvestorFlowOrm.date))
            .where(InvestorFlowOrm.investor_type == investor_type)
            .order_by(InvestorFlowOrm.date.desc())
            .limit(n)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def find_trend_by_stock(
        self, stock_code: str, since_date: date
    ) -> list[InvestorFlow]:
        stmt = (
            select(InvestorFlowOrm)
            .where(
                InvestorFlowOrm.stock_code == stock_code,
                InvestorFlowOrm.date >= since_date,
            )
            .order_by(InvestorFlowOrm.date.asc(), InvestorFlowOrm.investor_type.asc())
        )
        result = await self._db.execute(stmt)
        return [InvestorFlowMapper.to_entity(row) for row in result.scalars().all()]

    async def find_accumulated_flows(
        self, since_date: date, investor_type: str
    ) -> list[AccumulatedFlow]:
        # date >= since_date AND investor_type = X → GROUP BY stock_code → SUM(net_buy_amount)
        # 인덱스: date(단일), investor_type(단일) 활용 — 복합 인덱스 추가 시 성능 향상 가능
        total_col = func.sum(InvestorFlowOrm.net_buy_amount).label("total_net_buy")
        name_col = func.max(InvestorFlowOrm.stock_name).label("stock_name")
        stmt = (
            select(InvestorFlowOrm.stock_code, name_col, total_col)
            .where(
                InvestorFlowOrm.date >= since_date,
                InvestorFlowOrm.investor_type == investor_type,
            )
            .group_by(InvestorFlowOrm.stock_code)
            .having(total_col > 0)
            .order_by(total_col.desc())
        )
        result = await self._db.execute(stmt)
        return [
            AccumulatedFlow(
                stock_code=row.stock_code,
                stock_name=row.stock_name,
                total_net_buy=row.total_net_buy,
            )
            for row in result.all()
        ]

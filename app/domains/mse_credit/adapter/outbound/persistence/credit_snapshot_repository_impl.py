from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.mse_credit.application.port.credit_snapshot_repository import (
    CreditSnapshotRepositoryPort,
)
from app.domains.mse_credit.domain.entity.credit_snapshot import CreditSnapshot
from app.domains.mse_credit.domain.value_object.crawl_status import CrawlStatus
from app.domains.mse_credit.infrastructure.mapper.credit_snapshot_mapper import (
    CreditSnapshotMapper,
)
from app.domains.mse_credit.infrastructure.orm.credit_snapshot_orm import CreditSnapshotOrm


class CreditSnapshotRepositoryImpl(CreditSnapshotRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def save(self, snapshot: CreditSnapshot) -> CreditSnapshot:
        orm = CreditSnapshotMapper.to_orm(snapshot)
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        return CreditSnapshotMapper.to_entity(orm)

    async def find_latest(self) -> Optional[CreditSnapshot]:
        stmt = (
            select(CreditSnapshotOrm)
            .order_by(CreditSnapshotOrm.collected_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        return CreditSnapshotMapper.to_entity(orm) if orm else None

    async def find_latest_successful(self) -> Optional[CreditSnapshot]:
        stmt = (
            select(CreditSnapshotOrm)
            .where(CreditSnapshotOrm.status == CrawlStatus.SUCCESS.value)
            .order_by(CreditSnapshotOrm.collected_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        return CreditSnapshotMapper.to_entity(orm) if orm else None

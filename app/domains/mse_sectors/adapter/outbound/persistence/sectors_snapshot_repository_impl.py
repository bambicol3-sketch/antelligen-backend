from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.mse_sectors.application.port.sectors_snapshot_repository import (
    SectorsSnapshotRepositoryPort,
)
from app.domains.mse_sectors.domain.entity.sectors_snapshot import SectorsSnapshot
from app.domains.mse_sectors.domain.value_object.crawl_status import CrawlStatus
from app.domains.mse_sectors.infrastructure.mapper.sectors_snapshot_mapper import (
    SectorsSnapshotMapper,
)
from app.domains.mse_sectors.infrastructure.orm.sectors_snapshot_orm import SectorsSnapshotOrm


class SectorsSnapshotRepositoryImpl(SectorsSnapshotRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def save(self, snapshot: SectorsSnapshot) -> SectorsSnapshot:
        orm = SectorsSnapshotMapper.to_orm(snapshot)
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        return SectorsSnapshotMapper.to_entity(orm)

    async def find_latest(self) -> Optional[SectorsSnapshot]:
        stmt = (
            select(SectorsSnapshotOrm)
            .order_by(SectorsSnapshotOrm.collected_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        return SectorsSnapshotMapper.to_entity(orm) if orm else None

    async def find_latest_successful(self) -> Optional[SectorsSnapshot]:
        stmt = (
            select(SectorsSnapshotOrm)
            .where(SectorsSnapshotOrm.status == CrawlStatus.SUCCESS.value)
            .order_by(SectorsSnapshotOrm.collected_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        return SectorsSnapshotMapper.to_entity(orm) if orm else None

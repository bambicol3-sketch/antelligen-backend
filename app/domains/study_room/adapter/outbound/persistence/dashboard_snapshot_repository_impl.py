from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.study_room.application.port.dashboard_snapshot_repository import (
    DashboardSnapshotRepositoryPort,
)
from app.domains.study_room.domain.entity.dashboard_snapshot import DashboardSnapshot
from app.domains.study_room.domain.value_object.crawl_status import CrawlStatus
from app.domains.study_room.infrastructure.mapper.dashboard_snapshot_mapper import (
    DashboardSnapshotMapper,
)
from app.domains.study_room.infrastructure.orm.dashboard_snapshot_orm import (
    DashboardSnapshotOrm,
)


class DashboardSnapshotRepositoryImpl(DashboardSnapshotRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def save(self, snapshot: DashboardSnapshot) -> DashboardSnapshot:
        orm = DashboardSnapshotMapper.to_orm(snapshot)
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        return DashboardSnapshotMapper.to_entity(orm)

    async def find_latest(self) -> Optional[DashboardSnapshot]:
        stmt = (
            select(DashboardSnapshotOrm)
            .order_by(DashboardSnapshotOrm.collected_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        return DashboardSnapshotMapper.to_entity(orm) if orm else None

    async def find_latest_successful(self) -> Optional[DashboardSnapshot]:
        stmt = (
            select(DashboardSnapshotOrm)
            .where(DashboardSnapshotOrm.status == CrawlStatus.SUCCESS.value)
            .order_by(DashboardSnapshotOrm.collected_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        return DashboardSnapshotMapper.to_entity(orm) if orm else None

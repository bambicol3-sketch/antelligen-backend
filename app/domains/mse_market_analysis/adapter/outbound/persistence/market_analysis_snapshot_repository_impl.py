from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.mse_market_analysis.application.port.market_analysis_snapshot_repository import (
    MarketAnalysisSnapshotRepositoryPort,
)
from app.domains.mse_market_analysis.domain.entity.market_analysis_snapshot import (
    MarketAnalysisSnapshot,
)
from app.domains.mse_market_analysis.domain.value_object.crawl_status import CrawlStatus
from app.domains.mse_market_analysis.infrastructure.mapper.market_analysis_snapshot_mapper import (
    MarketAnalysisSnapshotMapper,
)
from app.domains.mse_market_analysis.infrastructure.orm.market_analysis_snapshot_orm import (
    MarketAnalysisSnapshotOrm,
)


class MarketAnalysisSnapshotRepositoryImpl(MarketAnalysisSnapshotRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def save(self, snapshot: MarketAnalysisSnapshot) -> MarketAnalysisSnapshot:
        orm = MarketAnalysisSnapshotMapper.to_orm(snapshot)
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        return MarketAnalysisSnapshotMapper.to_entity(orm)

    async def find_latest(self) -> Optional[MarketAnalysisSnapshot]:
        stmt = (
            select(MarketAnalysisSnapshotOrm)
            .order_by(MarketAnalysisSnapshotOrm.collected_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        return MarketAnalysisSnapshotMapper.to_entity(orm) if orm else None

    async def find_latest_successful(self) -> Optional[MarketAnalysisSnapshot]:
        stmt = (
            select(MarketAnalysisSnapshotOrm)
            .where(MarketAnalysisSnapshotOrm.status == CrawlStatus.SUCCESS.value)
            .order_by(MarketAnalysisSnapshotOrm.collected_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        return MarketAnalysisSnapshotMapper.to_entity(orm) if orm else None

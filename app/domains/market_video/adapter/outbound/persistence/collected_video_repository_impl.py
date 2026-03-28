from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_video.application.port.out.collected_video_repository_port import CollectedVideoRepositoryPort
from app.domains.market_video.domain.entity.collected_video import CollectedVideo
from app.domains.market_video.infrastructure.mapper.collected_video_mapper import CollectedVideoMapper
from app.domains.market_video.infrastructure.orm.collected_video_orm import CollectedVideoOrm


class CollectedVideoRepositoryImpl(CollectedVideoRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_video_id(self, video_id: str) -> Optional[CollectedVideo]:
        stmt = select(CollectedVideoOrm).where(CollectedVideoOrm.video_id == video_id)
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        return CollectedVideoMapper.to_entity(orm) if orm else None

    async def find_all(self) -> list[CollectedVideo]:
        stmt = select(CollectedVideoOrm)
        result = await self._db.execute(stmt)
        orm_list = result.scalars().all()
        return [CollectedVideoMapper.to_entity(orm) for orm in orm_list]

    async def upsert(self, video: CollectedVideo) -> CollectedVideo:
        stmt = select(CollectedVideoOrm).where(CollectedVideoOrm.video_id == video.video_id)
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.title = video.title
            orm.channel_name = video.channel_name
            orm.published_at = video.published_at
            orm.view_count = video.view_count
            orm.thumbnail_url = video.thumbnail_url
            orm.video_url = video.video_url
        else:
            orm = CollectedVideoMapper.to_orm(video)
            self._db.add(orm)

        await self._db.commit()
        await self._db.refresh(orm)
        return CollectedVideoMapper.to_entity(orm)

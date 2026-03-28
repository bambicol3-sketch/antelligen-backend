from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_video.application.port.out.video_comment_repository_port import VideoCommentRepositoryPort
from app.domains.market_video.domain.entity.video_comment import VideoComment
from app.domains.market_video.infrastructure.mapper.video_comment_mapper import VideoCommentMapper
from app.domains.market_video.infrastructure.orm.video_comment_orm import VideoCommentOrm


class VideoCommentRepositoryImpl(VideoCommentRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def save_all(self, comments: list[VideoComment]) -> None:
        if not comments:
            return

        comment_ids = [c.comment_id for c in comments]
        stmt = select(VideoCommentOrm.comment_id).where(VideoCommentOrm.comment_id.in_(comment_ids))
        result = await self._db.execute(stmt)
        existing_ids = set(result.scalars().all())

        new_comments = [c for c in comments if c.comment_id not in existing_ids]
        for comment in new_comments:
            self._db.add(VideoCommentMapper.to_orm(comment))

        if new_comments:
            await self._db.commit()

    async def find_all(self) -> list[VideoComment]:
        stmt = select(VideoCommentOrm)
        result = await self._db.execute(stmt)
        return [VideoCommentMapper.to_entity(orm) for orm in result.scalars().all()]

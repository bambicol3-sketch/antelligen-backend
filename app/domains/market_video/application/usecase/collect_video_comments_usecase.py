import logging

from app.domains.market_video.application.port.out.collected_video_repository_port import CollectedVideoRepositoryPort
from app.domains.market_video.application.port.out.comment_fetch_port import CommentFetchPort
from app.domains.market_video.application.port.out.video_comment_repository_port import VideoCommentRepositoryPort
from app.domains.market_video.application.response.video_comment_response import (
    CollectCommentsResponse,
    CommentItemResponse,
    VideoCommentResponse,
)
from app.domains.market_video.domain.entity.video_comment import VideoComment

logger = logging.getLogger(__name__)

MAX_COMMENTS_PER_VIDEO = 20
COMMENT_ORDER = "relevance"


class CollectVideoCommentsUseCase:
    def __init__(
        self,
        comment_fetch_port: CommentFetchPort,
        collected_video_repository: CollectedVideoRepositoryPort,
        video_comment_repository: VideoCommentRepositoryPort,
    ):
        self._comment_fetch = comment_fetch_port
        self._video_repository = collected_video_repository
        self._comment_repository = video_comment_repository

    async def execute(self) -> CollectCommentsResponse:
        stored_videos = await self._video_repository.find_all()

        if not stored_videos:
            return CollectCommentsResponse(total_comment_count=0, video_results=[])

        video_results = []
        total_count = 0

        for video in stored_videos:
            try:
                raw_comments = await self._comment_fetch.fetch_comments(
                    video_id=video.video_id,
                    max_count=MAX_COMMENTS_PER_VIDEO,
                    order=COMMENT_ORDER,
                )
            except Exception as e:
                logger.warning("[collect_comments] video_id=%s fetch error=%s", video.video_id, e)
                continue

            seen_ids: set[str] = set()
            comments_to_save: list[VideoComment] = []
            comment_responses: list[CommentItemResponse] = []

            for item in raw_comments:
                if not item.content.strip():
                    continue
                if item.comment_id in seen_ids:
                    continue
                seen_ids.add(item.comment_id)

                comments_to_save.append(VideoComment(
                    comment_id=item.comment_id,
                    video_id=video.video_id,
                    author_name=item.author_name,
                    content=item.content,
                    published_at=item.published_at,
                    like_count=item.like_count,
                ))
                comment_responses.append(CommentItemResponse(
                    comment_id=item.comment_id,
                    author_name=item.author_name,
                    content=item.content,
                    published_at=item.published_at,
                    like_count=item.like_count,
                ))

            try:
                await self._comment_repository.save_all(comments_to_save)
            except Exception as e:
                logger.warning("[collect_comments] DB 저장 실패 video_id=%s: %s", video.video_id, e)

            video_results.append(VideoCommentResponse(
                video_id=video.video_id,
                comments=comment_responses,
                comment_count=len(comment_responses),
            ))
            total_count += len(comment_responses)

        return CollectCommentsResponse(
            total_comment_count=total_count,
            video_results=video_results,
        )

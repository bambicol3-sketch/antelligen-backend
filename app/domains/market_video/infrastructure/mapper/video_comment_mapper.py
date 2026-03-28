from app.domains.market_video.domain.entity.video_comment import VideoComment
from app.domains.market_video.infrastructure.orm.video_comment_orm import VideoCommentOrm


class VideoCommentMapper:

    @staticmethod
    def to_entity(orm: VideoCommentOrm) -> VideoComment:
        return VideoComment(
            id=orm.id,
            comment_id=orm.comment_id,
            video_id=orm.video_id,
            author_name=orm.author_name,
            content=orm.content,
            published_at=orm.published_at,
            like_count=orm.like_count,
        )

    @staticmethod
    def to_orm(comment: VideoComment) -> VideoCommentOrm:
        return VideoCommentOrm(
            comment_id=comment.comment_id,
            video_id=comment.video_id,
            author_name=comment.author_name,
            content=comment.content,
            published_at=comment.published_at,
            like_count=comment.like_count,
        )

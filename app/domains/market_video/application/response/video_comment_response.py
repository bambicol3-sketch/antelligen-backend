from datetime import datetime

from pydantic import BaseModel


class CommentItemResponse(BaseModel):
    comment_id: str
    author_name: str
    content: str
    published_at: datetime
    like_count: int


class VideoCommentResponse(BaseModel):
    video_id: str
    comments: list[CommentItemResponse]
    comment_count: int


class CollectCommentsResponse(BaseModel):
    total_comment_count: int
    video_results: list[VideoCommentResponse]

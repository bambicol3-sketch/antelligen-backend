from datetime import datetime

from sqlalchemy import String, Text, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class VideoCommentOrm(Base):
    __tablename__ = "video_comment"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    comment_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    video_id: Mapped[str] = mapped_column(String(50), nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    like_count: Mapped[int] = mapped_column(BigInteger, default=0)

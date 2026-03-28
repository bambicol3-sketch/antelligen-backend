from datetime import datetime

from sqlalchemy import String, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class CollectedVideoOrm(Base):
    __tablename__ = "collected_video"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    channel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    view_count: Mapped[int] = mapped_column(BigInteger, default=0)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)
    video_url: Mapped[str] = mapped_column(String(255), nullable=False)

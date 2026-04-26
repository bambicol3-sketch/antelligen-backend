from datetime import date, datetime

from sqlalchemy import Date, Float, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class EventEnrichmentOrm(Base):
    __tablename__ = "event_enrichments"
    __table_args__ = (
        # v2: classifier_version을 UK에 포함하여 v1/v2 행 동시 보유. 동일 이벤트 재분류 시
        # v1을 보존하고 v2 행을 새로 추가한다.
        UniqueConstraint(
            "ticker", "event_date", "event_type", "detail_hash", "classifier_version",
            name="uq_event_enrichments_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    detail_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    causality: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    importance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    importance_score_1to5: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items_str: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # v2 분류기가 원본 event_type(보통 MAJOR_EVENT)을 재분류한 결과. v1 행은 NULL.
    reclassified_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    classifier_version: Mapped[str] = mapped_column(String(10), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

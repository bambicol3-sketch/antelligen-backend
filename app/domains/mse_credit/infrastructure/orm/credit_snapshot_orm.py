from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class CreditSnapshotOrm(Base):
    __tablename__ = "mse_credit_snapshot"
    __table_args__ = (
        Index("ix_mse_credit_collected_at", "collected_at"),
        Index("ix_mse_credit_status_collected", "status", "collected_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    stock_metrics: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    leading_industries: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

from datetime import date, datetime

from sqlalchemy import Date, DateTime, BigInteger, String, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class KrPortfolioOrm(Base):
    __tablename__ = "kr_portfolio"
    __table_args__ = (
        UniqueConstraint("investor_name", "stock_code", name="uq_kr_portfolio"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    investor_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    investor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    stock_name: Mapped[str] = mapped_column(String(200), nullable=False)
    shares_held: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    ownership_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 지분율 (%)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reported_at: Mapped[date] = mapped_column(Date, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

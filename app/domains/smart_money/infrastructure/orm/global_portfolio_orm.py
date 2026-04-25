from datetime import date, datetime

from sqlalchemy import Date, DateTime, BigInteger, String, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class GlobalPortfolioOrm(Base):
    __tablename__ = "global_portfolio"
    __table_args__ = (
        UniqueConstraint("investor_name", "cusip", "reported_at", name="uq_global_portfolio"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    investor_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stock_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cusip: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    shares: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    market_value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)  # USD 천 달러
    portfolio_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reported_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

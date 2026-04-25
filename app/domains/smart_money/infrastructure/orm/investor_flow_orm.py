from datetime import date, datetime

from sqlalchemy import Date, DateTime, BigInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class InvestorFlowOrm(Base):
    __tablename__ = "investor_flow"
    __table_args__ = (
        UniqueConstraint("date", "investor_type", "stock_code", name="uq_investor_flow"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    investor_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False)
    net_buy_amount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    net_buy_volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

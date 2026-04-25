from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class UserWatchlistOrm(Base):
    __tablename__ = "user_watchlist"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id", ondelete="CASCADE"), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (UniqueConstraint("account_id", "stock_code", name="uq_user_watchlist"),)

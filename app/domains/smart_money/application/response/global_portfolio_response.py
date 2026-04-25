from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.domains.smart_money.domain.entity.global_portfolio import ChangeType


class GlobalPortfolioItem(BaseModel):
    investor_name: str
    ticker: Optional[str]
    stock_name: str
    shares: int
    market_value: int       # USD 천 달러
    portfolio_weight: float # %
    change_type: ChangeType
    reported_at: date


class GlobalPortfolioResponse(BaseModel):
    investor_name: Optional[str]    # None이면 전체 투자자
    change_type: Optional[ChangeType]
    total: int
    items: list[GlobalPortfolioItem]


class InvestorListResponse(BaseModel):
    investors: list[str]

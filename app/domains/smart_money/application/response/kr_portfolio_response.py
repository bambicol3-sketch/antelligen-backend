from datetime import date
from typing import Optional

from pydantic import BaseModel


class KrPortfolioItem(BaseModel):
    investor_name: str
    investor_type: str
    stock_code: str
    stock_name: str
    shares_held: int
    ownership_ratio: float
    change_type: str
    reported_at: Optional[date]


class KrPortfolioResponse(BaseModel):
    investor_name: Optional[str]
    items: list[KrPortfolioItem]
    total: int


class KrInvestorListResponse(BaseModel):
    investors: list[dict]  # [{name: str, type: str}]


class CollectKrPortfolioResponse(BaseModel):
    total_saved: int
    message: str

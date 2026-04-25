from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.domains.smart_money.domain.entity.investor_flow import InvestorType


class InvestorFlowRankingItem(BaseModel):
    rank: int
    stock_code: str
    stock_name: str
    net_buy_amount: int
    net_buy_volume: int


class InvestorFlowRankingResponse(BaseModel):
    investor_type: InvestorType
    date: Optional[date]
    items: list[InvestorFlowRankingItem]

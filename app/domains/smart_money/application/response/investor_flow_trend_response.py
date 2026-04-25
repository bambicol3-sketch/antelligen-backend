from datetime import date
from typing import Optional

from pydantic import BaseModel


class InvestorFlowTrendPoint(BaseModel):
    date: date
    foreign: int        # 외국인 순매수 금액
    institution: int    # 기관 순매수 금액
    individual: int     # 개인 순매수 금액


class InvestorFlowTrendResponse(BaseModel):
    stock_code: str
    stock_name: str | None
    since_date: Optional[date]
    days: int
    points: list[InvestorFlowTrendPoint]

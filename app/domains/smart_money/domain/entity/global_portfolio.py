from datetime import date, datetime
from enum import Enum


class ChangeType(str, Enum):
    NEW = "NEW"
    INCREASED = "INCREASED"
    DECREASED = "DECREASED"
    CLOSED = "CLOSED"


class GlobalPortfolio:
    """글로벌 저명 투자자 분기별 포트폴리오 도메인 엔티티 — 순수 Python, 외부 의존성 없음"""

    def __init__(
        self,
        investor_name: str,
        ticker: str | None,
        stock_name: str,
        cusip: str,
        shares: int,
        market_value: int,          # USD 천 달러 단위 (SEC 13F 기준)
        portfolio_weight: float,    # % (소수점 4자리)
        reported_at: date,          # 13F period of report
        change_type: ChangeType,
        portfolio_id: int | None = None,
        collected_at: datetime | None = None,
    ):
        self.portfolio_id = portfolio_id
        self.investor_name = investor_name
        self.ticker = ticker
        self.stock_name = stock_name
        self.cusip = cusip
        self.shares = shares
        self.market_value = market_value
        self.portfolio_weight = portfolio_weight
        self.reported_at = reported_at
        self.change_type = change_type
        self.collected_at = collected_at

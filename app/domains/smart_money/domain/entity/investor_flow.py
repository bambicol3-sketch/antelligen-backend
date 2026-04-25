from datetime import date, datetime
from enum import Enum


class InvestorType(str, Enum):
    FOREIGN = "FOREIGN"
    INSTITUTION = "INSTITUTION"
    INDIVIDUAL = "INDIVIDUAL"


class InvestorFlow:
    """투자자 유형별 일별 순매수 도메인 엔티티 — 순수 Python, 외부 의존성 없음"""

    def __init__(
        self,
        date: date,
        investor_type: InvestorType,
        stock_code: str,
        stock_name: str,
        net_buy_amount: int,
        net_buy_volume: int,
        flow_id: int | None = None,
        collected_at: datetime | None = None,
    ):
        self.flow_id = flow_id
        self.date = date
        self.investor_type = investor_type
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.net_buy_amount = net_buy_amount    # 순매수 금액 (원)
        self.net_buy_volume = net_buy_volume    # 순매수 수량 (주)
        self.collected_at = collected_at

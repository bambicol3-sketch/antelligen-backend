from abc import ABC, abstractmethod
from datetime import date

from app.domains.smart_money.domain.entity.investor_flow import InvestorFlow


class KrxInvestorFlowPort(ABC):

    @abstractmethod
    async def fetch(self, target_date: date) -> list[InvestorFlow]:
        """지정 날짜의 투자자 유형별 전 종목 순매수 데이터를 반환한다."""
        pass

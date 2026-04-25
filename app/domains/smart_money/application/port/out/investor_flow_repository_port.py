from abc import ABC, abstractmethod
from datetime import date

from app.domains.smart_money.domain.entity.investor_flow import InvestorFlow
from app.domains.smart_money.domain.service.smart_money_domain_service import AccumulatedFlow


class InvestorFlowRepositoryPort(ABC):

    @abstractmethod
    async def exists(self, target_date: date, investor_type: str, stock_code: str) -> bool:
        pass

    @abstractmethod
    async def save_batch(self, flows: list[InvestorFlow]) -> int:
        """중복을 제외하고 저장 후 실제 저장된 건수를 반환한다."""
        pass

    @abstractmethod
    async def find_ranking(
        self, target_date: date, investor_type: str, limit: int
    ) -> list[InvestorFlow]:
        """순매수 금액 내림차순으로 종목 랭킹을 반환한다."""
        pass

    @abstractmethod
    async def find_latest_date(self, investor_type: str) -> date | None:
        """해당 투자자 유형의 가장 최근 수집 날짜를 반환한다."""
        pass

    @abstractmethod
    async def find_recent_dates(self, investor_type: str, n: int) -> list[date]:
        """해당 투자자 유형의 최근 N 영업일 날짜 목록을 반환한다."""
        pass

    @abstractmethod
    async def find_accumulated_flows(
        self, since_date: date, investor_type: str
    ) -> list[AccumulatedFlow]:
        """since_date 이후 investor_type별 종목 누적 순매수 금액을 반환한다 (양수만, 내림차순)."""
        pass

    @abstractmethod
    async def find_trend_by_stock(
        self, stock_code: str, since_date: date
    ) -> list[InvestorFlow]:
        """특정 종목의 since_date 이후 모든 투자자 유형 일별 순매수 데이터를 반환한다."""
        pass

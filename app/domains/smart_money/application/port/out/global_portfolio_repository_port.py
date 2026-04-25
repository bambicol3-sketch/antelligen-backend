from abc import ABC, abstractmethod
from datetime import date

from app.domains.smart_money.domain.entity.global_portfolio import ChangeType, GlobalPortfolio


class GlobalPortfolioRepositoryPort(ABC):

    @abstractmethod
    async def find_previous_holdings(
        self, investor_name: str, before_date: date
    ) -> list[GlobalPortfolio]:
        """지정 날짜 이전 가장 최근 분기의 보유 종목을 반환한다."""
        pass

    @abstractmethod
    async def exists_for_period(self, investor_name: str, reported_at: date) -> bool:
        """해당 분기 데이터가 이미 수집되어 있는지 확인한다."""
        pass

    @abstractmethod
    async def save_batch(self, portfolios: list[GlobalPortfolio]) -> int:
        pass

    @abstractmethod
    async def find_latest(
        self,
        investor_name: str | None = None,
        change_type: ChangeType | None = None,
    ) -> list[GlobalPortfolio]:
        """최신 분기 포트폴리오를 반환한다. investor_name/change_type으로 필터링 가능."""
        pass

    @abstractmethod
    async def find_investor_names(self) -> list[str]:
        """수집된 투자자 이름 목록을 반환한다."""
        pass

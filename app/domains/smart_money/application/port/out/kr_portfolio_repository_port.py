from abc import ABC, abstractmethod

from app.domains.smart_money.domain.entity.kr_portfolio import KrPortfolioHolding


class KrPortfolioRepositoryPort(ABC):

    @abstractmethod
    async def find_by_investor(self, investor_name: str) -> list[KrPortfolioHolding]:
        """투자자명으로 보유 종목 목록을 반환한다 (지분율 내림차순)."""
        pass

    @abstractmethod
    async def find_one(self, investor_name: str, stock_code: str) -> KrPortfolioHolding | None:
        """특정 투자자의 특정 종목 보유 현황을 반환한다."""
        pass

    @abstractmethod
    async def upsert(self, holding: KrPortfolioHolding) -> None:
        """보유 현황을 저장하거나 기존 레코드를 갱신한다 (ON CONFLICT DO UPDATE)."""
        pass

    @abstractmethod
    async def find_all_investor_names(self) -> list[str]:
        """DB에 수집된 투자자 이름 목록을 반환한다."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """저장된 전체 보유 레코드 수를 반환한다."""
        pass

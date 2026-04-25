from abc import ABC, abstractmethod

from app.domains.smart_money.domain.entity.global_portfolio import GlobalPortfolio


class GlobalPortfolioFetchPort(ABC):

    @abstractmethod
    async def fetch_latest(self, investor_name: str, cik: str) -> list[GlobalPortfolio]:
        """지정 CIK의 최신 13F 공시에서 포트폴리오 데이터를 수집하여 반환한다.
        reported_at은 포함되어 있으나 change_type은 NONE — UseCase에서 계산된다."""
        pass

from abc import ABC, abstractmethod
from typing import Optional

from app.domains.agent.application.response.integrated_analysis_response import IntegratedAnalysisResponse


class IntegratedAnalysisRepositoryPort(ABC):
    @abstractmethod
    async def find_recent(self, ticker: str, within_seconds: int) -> Optional[IntegratedAnalysisResponse]:
        """최근 within_seconds 이내 분석 결과 반환. 없으면 None."""
        pass

    @abstractmethod
    async def save(self, result: IntegratedAnalysisResponse) -> None:
        pass

    @abstractmethod
    async def find_history(self, ticker: str, limit: int = 10) -> list[IntegratedAnalysisResponse]:
        """ticker 기준 최근 분석 이력 반환."""
        pass

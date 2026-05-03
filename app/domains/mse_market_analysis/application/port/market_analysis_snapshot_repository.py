from abc import ABC, abstractmethod
from typing import Optional

from app.domains.mse_market_analysis.domain.entity.market_analysis_snapshot import (
    MarketAnalysisSnapshot,
)


class MarketAnalysisSnapshotRepositoryPort(ABC):
    @abstractmethod
    async def save(self, snapshot: MarketAnalysisSnapshot) -> MarketAnalysisSnapshot:
        pass

    @abstractmethod
    async def find_latest(self) -> Optional[MarketAnalysisSnapshot]:
        pass

    @abstractmethod
    async def find_latest_successful(self) -> Optional[MarketAnalysisSnapshot]:
        pass

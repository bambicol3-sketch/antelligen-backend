from abc import ABC, abstractmethod
from typing import Optional

from app.domains.mse_credit.domain.entity.credit_snapshot import CreditSnapshot


class CreditSnapshotRepositoryPort(ABC):
    @abstractmethod
    async def save(self, snapshot: CreditSnapshot) -> CreditSnapshot:
        pass

    @abstractmethod
    async def find_latest(self) -> Optional[CreditSnapshot]:
        pass

    @abstractmethod
    async def find_latest_successful(self) -> Optional[CreditSnapshot]:
        pass

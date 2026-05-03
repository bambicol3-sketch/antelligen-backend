from abc import ABC, abstractmethod
from typing import Optional

from app.domains.mse_sectors.domain.entity.sectors_snapshot import SectorsSnapshot


class SectorsSnapshotRepositoryPort(ABC):
    @abstractmethod
    async def save(self, snapshot: SectorsSnapshot) -> SectorsSnapshot:
        pass

    @abstractmethod
    async def find_latest(self) -> Optional[SectorsSnapshot]:
        pass

    @abstractmethod
    async def find_latest_successful(self) -> Optional[SectorsSnapshot]:
        pass

from abc import ABC, abstractmethod
from typing import Optional

from app.domains.study_room.domain.entity.dashboard_snapshot import DashboardSnapshot


class DashboardSnapshotRepositoryPort(ABC):
    @abstractmethod
    async def save(self, snapshot: DashboardSnapshot) -> DashboardSnapshot:
        pass

    @abstractmethod
    async def find_latest(self) -> Optional[DashboardSnapshot]:
        pass

    @abstractmethod
    async def find_latest_successful(self) -> Optional[DashboardSnapshot]:
        pass

from abc import ABC, abstractmethod

from app.domains.hermes.domain.entity.hermes_entry import HermesEntry


class HermesRepositoryPort(ABC):
    @abstractmethod
    async def find_all(self) -> list[HermesEntry]:
        """전체 엔트리 — updated_at 내림차순."""
        ...

    @abstractmethod
    async def find_by_id(self, entry_id: str) -> HermesEntry | None:
        ...

    @abstractmethod
    async def save(self, entry: HermesEntry) -> HermesEntry:
        """생성/수정 공용 upsert. 저장 후 인덱스를 재생성한다."""
        ...

    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        ...

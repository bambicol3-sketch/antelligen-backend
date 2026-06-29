from abc import ABC, abstractmethod

from app.domains.hermes.domain.entity.agent_blueprint import AgentBlueprint


class AgentBlueprintRepositoryPort(ABC):
    @abstractmethod
    async def find_all(self, owner: str | None = None) -> list[AgentBlueprint]:
        """owner 지정 시 해당 직원 소유분만, 미지정 시 전체 — updated_at 내림차순."""
        ...

    @abstractmethod
    async def find_by_id(self, blueprint_id: str) -> AgentBlueprint | None:
        ...

    @abstractmethod
    async def save(self, blueprint: AgentBlueprint) -> AgentBlueprint:
        """생성/수정 공용 upsert."""
        ...

    @abstractmethod
    async def delete(self, blueprint_id: str) -> bool:
        ...

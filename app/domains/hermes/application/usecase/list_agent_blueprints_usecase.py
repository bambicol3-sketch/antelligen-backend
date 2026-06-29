from app.domains.hermes.application.port.agent_blueprint_repository_port import (
    AgentBlueprintRepositoryPort,
)
from app.domains.hermes.application.response.agent_blueprint_response import (
    AgentBlueprintResponse,
)


class ListAgentBlueprintsUseCase:
    def __init__(self, repository: AgentBlueprintRepositoryPort):
        self._repository = repository

    async def execute(self, owner: str | None = None) -> list[AgentBlueprintResponse]:
        blueprints = await self._repository.find_all(owner=owner)
        return [AgentBlueprintResponse.from_entity(b) for b in blueprints]

from app.domains.hermes.application.port.agent_blueprint_repository_port import (
    AgentBlueprintRepositoryPort,
)
from app.domains.hermes.application.response.agent_blueprint_response import (
    AgentBlueprintResponse,
)


class GetAgentBlueprintUseCase:
    def __init__(self, repository: AgentBlueprintRepositoryPort):
        self._repository = repository

    async def execute(self, blueprint_id: str) -> AgentBlueprintResponse | None:
        blueprint = await self._repository.find_by_id(blueprint_id)
        if blueprint is None:
            return None
        return AgentBlueprintResponse.from_entity(blueprint)

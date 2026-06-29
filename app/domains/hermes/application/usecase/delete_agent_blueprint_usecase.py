from app.domains.hermes.application.port.agent_blueprint_repository_port import (
    AgentBlueprintRepositoryPort,
)


class DeleteAgentBlueprintUseCase:
    def __init__(self, repository: AgentBlueprintRepositoryPort):
        self._repository = repository

    async def execute(self, blueprint_id: str) -> bool:
        return await self._repository.delete(blueprint_id)

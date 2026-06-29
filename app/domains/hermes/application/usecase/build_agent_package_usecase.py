from app.domains.hermes.application.port.agent_blueprint_repository_port import (
    AgentBlueprintRepositoryPort,
)
from app.domains.hermes.application.port.agent_package_builder_port import (
    AgentPackageBuilderPort,
    BuiltAgentPackage,
)


class BuildAgentPackageUseCase:
    """blueprint id 로 다운로드 가능한 에이전트 패키지(zip)를 빌드한다."""

    def __init__(
        self,
        repository: AgentBlueprintRepositoryPort,
        builder: AgentPackageBuilderPort,
    ):
        self._repository = repository
        self._builder = builder

    async def execute(self, blueprint_id: str) -> BuiltAgentPackage | None:
        blueprint = await self._repository.find_by_id(blueprint_id)
        if blueprint is None:
            return None
        return self._builder.build(blueprint)

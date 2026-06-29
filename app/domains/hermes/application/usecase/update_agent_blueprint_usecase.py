from datetime import datetime
from zoneinfo import ZoneInfo

from app.domains.hermes.application.port.agent_blueprint_repository_port import (
    AgentBlueprintRepositoryPort,
)
from app.domains.hermes.application.request.create_agent_blueprint_request import (
    CreateAgentBlueprintRequest,
)
from app.domains.hermes.application.response.agent_blueprint_response import (
    AgentBlueprintResponse,
)
from app.domains.hermes.application.usecase.create_agent_blueprint_usecase import (
    parse_capabilities,
    to_workflow_steps,
)
from app.domains.hermes.domain.entity.agent_blueprint import DEFAULT_AGENT_MODEL

_KST = ZoneInfo("Asia/Seoul")


class UpdateAgentBlueprintUseCase:
    def __init__(self, repository: AgentBlueprintRepositoryPort):
        self._repository = repository

    async def execute(
        self, blueprint_id: str, request: CreateAgentBlueprintRequest
    ) -> AgentBlueprintResponse | None:
        existing = await self._repository.find_by_id(blueprint_id)
        if existing is None:
            return None

        existing.owner = request.owner
        existing.title = request.title
        existing.goal = request.goal
        existing.workflow_steps = to_workflow_steps(request.workflow_steps)
        existing.capabilities = parse_capabilities(request.capabilities)
        existing.model = request.model or DEFAULT_AGENT_MODEL
        existing.updated_at = datetime.now(_KST)

        saved = await self._repository.save(existing)
        return AgentBlueprintResponse.from_entity(saved)

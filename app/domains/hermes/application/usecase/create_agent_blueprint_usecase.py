import uuid
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
from app.domains.hermes.domain.entity.agent_blueprint import (
    DEFAULT_AGENT_MODEL,
    AgentBlueprint,
)
from app.domains.hermes.domain.value_object.agent_capability import AgentCapability
from app.domains.hermes.domain.value_object.workflow_step import WorkflowStep

_KST = ZoneInfo("Asia/Seoul")


def parse_capabilities(values: list[str]) -> list[AgentCapability]:
    """알 수 없는 capability 값은 조용히 무시한다."""
    parsed = [AgentCapability.from_value(v) for v in values]
    return [c for c in parsed if c is not None]


def to_workflow_steps(step_inputs) -> list[WorkflowStep]:
    return [
        WorkflowStep(
            order=idx + 1,
            instruction=s.instruction,
            inputs=s.inputs,
            expected_output=s.expected_output,
        )
        for idx, s in enumerate(step_inputs)
    ]


class CreateAgentBlueprintUseCase:
    def __init__(self, repository: AgentBlueprintRepositoryPort):
        self._repository = repository

    async def execute(self, request: CreateAgentBlueprintRequest) -> AgentBlueprintResponse:
        now = datetime.now(_KST)
        entity = AgentBlueprint(
            id=uuid.uuid4().hex[:12],
            owner=request.owner,
            title=request.title,
            goal=request.goal,
            workflow_steps=to_workflow_steps(request.workflow_steps),
            capabilities=parse_capabilities(request.capabilities),
            model=request.model or DEFAULT_AGENT_MODEL,
            created_at=now,
            updated_at=now,
        )
        saved = await self._repository.save(entity)
        return AgentBlueprintResponse.from_entity(saved)

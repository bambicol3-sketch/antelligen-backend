from datetime import datetime

from pydantic import BaseModel

from app.domains.hermes.domain.entity.agent_blueprint import AgentBlueprint


class WorkflowStepResponse(BaseModel):
    order: int
    instruction: str
    inputs: list[str]
    expected_output: str


class AgentBlueprintResponse(BaseModel):
    id: str
    owner: str
    title: str
    goal: str
    workflow_steps: list[WorkflowStepResponse]
    capabilities: list[str]
    model: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_entity(cls, entity: AgentBlueprint) -> "AgentBlueprintResponse":
        return cls(
            id=entity.id,
            owner=entity.owner,
            title=entity.title,
            goal=entity.goal,
            workflow_steps=[
                WorkflowStepResponse(
                    order=s.order,
                    instruction=s.instruction,
                    inputs=s.inputs,
                    expected_output=s.expected_output,
                )
                for s in entity.workflow_steps
            ],
            capabilities=[c.value for c in entity.capabilities],
            model=entity.model,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

from datetime import datetime

from app.domains.hermes.domain.entity.agent_blueprint import (
    DEFAULT_AGENT_MODEL,
    AgentBlueprint,
)
from app.domains.hermes.domain.value_object.agent_capability import AgentCapability
from app.domains.hermes.domain.value_object.workflow_step import WorkflowStep


class AgentBlueprintMapper:
    """AgentBlueprint ↔ 저장용 dict(JSON) 변환. (ORM 미사용 — 파일 저장소 전용)"""

    @staticmethod
    def to_dict(blueprint: AgentBlueprint) -> dict:
        return {
            "id": blueprint.id,
            "owner": blueprint.owner,
            "title": blueprint.title,
            "goal": blueprint.goal,
            "workflow_steps": [
                {
                    "order": s.order,
                    "instruction": s.instruction,
                    "inputs": s.inputs,
                    "expected_output": s.expected_output,
                }
                for s in blueprint.workflow_steps
            ],
            "capabilities": [c.value for c in blueprint.capabilities],
            "model": blueprint.model,
            "created_at": blueprint.created_at.isoformat() if blueprint.created_at else None,
            "updated_at": blueprint.updated_at.isoformat() if blueprint.updated_at else None,
        }

    @staticmethod
    def to_entity(data: dict) -> AgentBlueprint:
        return AgentBlueprint(
            id=data["id"],
            owner=data.get("owner", ""),
            title=data.get("title", ""),
            goal=data.get("goal", ""),
            workflow_steps=[
                WorkflowStep(
                    order=s.get("order", idx + 1),
                    instruction=s.get("instruction", ""),
                    inputs=list(s.get("inputs", [])),
                    expected_output=s.get("expected_output", ""),
                )
                for idx, s in enumerate(data.get("workflow_steps", []))
            ],
            capabilities=[
                cap
                for cap in (AgentCapability.from_value(v) for v in data.get("capabilities", []))
                if cap is not None
            ],
            model=data.get("model") or DEFAULT_AGENT_MODEL,
            created_at=AgentBlueprintMapper._parse_dt(data.get("created_at")),
            updated_at=AgentBlueprintMapper._parse_dt(data.get("updated_at")),
        )

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

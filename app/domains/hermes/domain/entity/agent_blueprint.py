import re
from dataclasses import dataclass, field
from datetime import datetime

from app.domains.hermes.domain.value_object.agent_capability import AgentCapability
from app.domains.hermes.domain.value_object.workflow_step import WorkflowStep

# 게이트웨이/프록시 매핑명으로 오버라이드 가능 (런타임 env: HERMES_AGENT_MODEL)
DEFAULT_AGENT_MODEL = "claude-opus-4-8"


@dataclass
class AgentBlueprint:
    """'1인 1 에이전트' 설계도. 직원이 입력한 워크플로우로부터 다운로드 가능한
    에이전트 패키지를 생성하기 위한 모든 정보를 담는다. (순수 도메인 — 외부 의존 없음)"""

    id: str
    owner: str                       # 직원 식별자
    title: str
    goal: str = ""                   # KPI 프레이밍(자유 서술)
    workflow_steps: list[WorkflowStep] = field(default_factory=list)
    capabilities: list[AgentCapability] = field(default_factory=list)
    model: str = DEFAULT_AGENT_MODEL
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def has_capability(self, capability: AgentCapability) -> bool:
        return capability in self.capabilities

    def package_name(self) -> str:
        """zip 루트 디렉터리/파일명에 쓸 ASCII 안전 슬러그.
        한글 등 비-ASCII 제목이면 id 기반으로 폴백한다."""
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", self.title).strip("-").lower()
        if not slug:
            slug = f"agent-{self.id[:8]}"
        return f"{slug}-agent"

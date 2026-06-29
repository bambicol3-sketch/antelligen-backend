from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domains.hermes.domain.entity.agent_blueprint import AgentBlueprint


@dataclass
class BuiltAgentPackage:
    """빌드 결과 — 다운로드 가능한 zip 바이트와 메타."""

    filename: str
    content: bytes
    package_name: str
    capabilities: list[str]


class AgentPackageBuilderPort(ABC):
    @abstractmethod
    def build(self, blueprint: AgentBlueprint) -> BuiltAgentPackage:
        """blueprint → 자립 실행 가능한 에이전트 패키지(zip) 바이트."""
        ...

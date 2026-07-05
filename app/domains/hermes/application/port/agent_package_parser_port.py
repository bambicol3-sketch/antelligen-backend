from abc import ABC, abstractmethod

from app.domains.hermes.domain.entity.agent_blueprint import AgentBlueprint


class AgentPackageParserPort(ABC):
    """업로드된 에이전트 패키지(zip) → AgentBlueprint 복원. (build 의 역방향)"""

    @abstractmethod
    def parse(self, content: bytes) -> AgentBlueprint | None:
        """zip 바이트에서 blueprint manifest 를 읽어 엔티티로 복원한다.
        manifest 가 없거나 손상돼 복원 불가하면 None 을 반환한다."""
        ...

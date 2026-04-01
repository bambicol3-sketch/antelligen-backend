from abc import ABC, abstractmethod

from app.domains.agent.application.response.sub_agent_response import SubAgentResponse


class LlmSynthesisPort(ABC):
    @abstractmethod
    async def synthesize(
        self,
        ticker: str,
        query: str,
        sub_results: list[SubAgentResponse],
    ) -> tuple[str, list[str]]:
        """서브에이전트 결과를 종합하여 (summary, key_points) 반환."""
        pass

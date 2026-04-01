from abc import ABC, abstractmethod

from app.domains.agent.application.response.sub_agent_response import SubAgentResponse


class DisclosureAgentPort(ABC):
    @abstractmethod
    async def analyze(self, ticker: str) -> SubAgentResponse:
        pass

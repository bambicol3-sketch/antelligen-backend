from abc import ABC, abstractmethod

from app.domains.agent.application.response.sub_agent_response import SubAgentResponse


class NewsAgentPort(ABC):
    @abstractmethod
    async def analyze(self, ticker: str, query: str) -> SubAgentResponse:
        pass

from abc import ABC, abstractmethod

from app.domains.agent.application.response.sub_agent_response import SubAgentResponse


class SubAgentProvider(ABC):
    @abstractmethod
    def call(self, agent_name: str, ticker: str | None, query: str) -> SubAgentResponse:
        pass

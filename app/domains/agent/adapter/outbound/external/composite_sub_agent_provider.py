from app.domains.agent.application.port.sub_agent_provider import SubAgentProvider
from app.domains.agent.application.response.sub_agent_response import SubAgentResponse


class CompositeSubAgentProvider(SubAgentProvider):
    def __init__(self, providers: dict[str, SubAgentProvider]):
        self._providers = providers

    def call(self, agent_name: str, ticker: str | None, query: str) -> SubAgentResponse:
        provider = self._providers.get(agent_name)
        if provider is None:
            return SubAgentResponse.error(
                agent_name,
                f"등록되지 않은 에이전트: {agent_name}",
                0,
            )
        return provider.call(agent_name, ticker, query)

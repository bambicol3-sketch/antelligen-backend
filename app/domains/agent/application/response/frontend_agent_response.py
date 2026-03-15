from typing import Any, Optional

from pydantic import BaseModel

from app.domains.agent.application.response.agent_query_response import (
    AgentQueryResponse,
    QueryResultStatus,
)


class FrontendAgentResultItem(BaseModel):
    agent_name: str
    status: str
    data: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: int


class FrontendAgentResponse(BaseModel):
    session_id: str
    result_status: QueryResultStatus
    answer: str
    agent_results: list[FrontendAgentResultItem]
    total_execution_time_ms: int

    @classmethod
    def from_internal(cls, response: AgentQueryResponse) -> "FrontendAgentResponse":
        agent_results = [
            FrontendAgentResultItem(
                agent_name=r.agent_name,
                status=r.status.value,
                data=r.data,
                error_message=r.error_message,
                execution_time_ms=r.execution_time_ms,
            )
            for r in response.agent_results
        ]

        return cls(
            session_id=response.session_id,
            result_status=response.result_status,
            answer=response.answer,
            agent_results=agent_results,
            total_execution_time_ms=response.total_execution_time_ms,
        )

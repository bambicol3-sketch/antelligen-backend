from fastapi import APIRouter

from app.common.response.base_response import BaseResponse
from app.domains.agent.adapter.outbound.external.mock_sub_agent_provider import (
    MockSubAgentProvider,
)
from app.domains.agent.application.request.agent_query_request import AgentQueryRequest
from app.domains.agent.application.response.frontend_agent_response import (
    FrontendAgentResponse,
)
from app.domains.agent.application.usecase.process_agent_query_usecase import (
    ProcessAgentQueryUseCase,
)

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post(
    "/query",
    response_model=BaseResponse[FrontendAgentResponse],
    status_code=200,
)
async def query_agent(request: AgentQueryRequest):
    provider = MockSubAgentProvider()
    usecase = ProcessAgentQueryUseCase(provider)
    internal_result = usecase.execute(request)
    frontend_result = FrontendAgentResponse.from_internal(internal_result)
    return BaseResponse.ok(data=frontend_result)

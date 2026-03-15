from fastapi import APIRouter, Request

from app.domains.api_schema.adapter.outbound.external.fastapi_endpoint_collector import (
    FastApiEndpointCollector,
)
from app.domains.api_schema.application.response.agent_schema_response import (
    AgentSchemaResponse,
)
from app.domains.api_schema.application.usecase.generate_agent_schema_usecase import (
    GenerateAgentSchemaUseCase,
)

router = APIRouter(prefix="/agent-schema", tags=["Agent Schema"])


@router.get("", response_model=AgentSchemaResponse)
async def get_agent_schema(request: Request):
    app = request.app
    base_url = str(request.base_url).rstrip("/")

    collector = FastApiEndpointCollector(app)
    usecase = GenerateAgentSchemaUseCase(collector, api_base_url=base_url)
    return usecase.execute()

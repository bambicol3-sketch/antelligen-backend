# HERMES Agent Factory — '1인 1 에이전트' 생성/다운로드 API
# 직원이 워크플로우를 입력하면 AgentBlueprint 를 만들고, 다운로드 시 자립 실행 에이전트(zip)를 빌드한다.
# Inbound 어댑터 규칙: Request → UseCase → Response 흐름만. 비즈니스 로직 금지.

import logging

from fastapi import APIRouter, Query, Response

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.hermes.adapter.outbound.packaging.zip_agent_package_builder import (
    ZipAgentPackageBuilder,
)
from app.domains.hermes.adapter.outbound.persistence.agent_blueprint_repository_impl import (
    AgentBlueprintRepositoryImpl,
)
from app.domains.hermes.application.request.create_agent_blueprint_request import (
    CreateAgentBlueprintRequest,
)
from app.domains.hermes.application.usecase.build_agent_package_usecase import (
    BuildAgentPackageUseCase,
)
from app.domains.hermes.application.usecase.create_agent_blueprint_usecase import (
    CreateAgentBlueprintUseCase,
)
from app.domains.hermes.application.usecase.delete_agent_blueprint_usecase import (
    DeleteAgentBlueprintUseCase,
)
from app.domains.hermes.application.usecase.get_agent_blueprint_usecase import (
    GetAgentBlueprintUseCase,
)
from app.domains.hermes.application.usecase.list_agent_blueprints_usecase import (
    ListAgentBlueprintsUseCase,
)
from app.domains.hermes.application.usecase.update_agent_blueprint_usecase import (
    UpdateAgentBlueprintUseCase,
)
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hermes/agents", tags=["hermes-agents"])


def _repository() -> AgentBlueprintRepositoryImpl:
    return AgentBlueprintRepositoryImpl(get_settings().hermes_agent_store_dir)


def _builder() -> ZipAgentPackageBuilder:
    return ZipAgentPackageBuilder()


@router.get("")
async def list_agents(owner: str | None = Query(None, description="직원 식별자로 필터")):
    usecase = ListAgentBlueprintsUseCase(_repository())
    data = await usecase.execute(owner=owner)
    return BaseResponse.ok(data=data, message="에이전트 설계도 목록 조회 성공")


@router.get("/{blueprint_id}")
async def get_agent(blueprint_id: str):
    usecase = GetAgentBlueprintUseCase(_repository())
    data = await usecase.execute(blueprint_id)
    if data is None:
        raise AppException(status_code=404, message="해당 에이전트 설계도를 찾을 수 없습니다.")
    return BaseResponse.ok(data=data, message="에이전트 설계도 조회 성공")


@router.post("")
async def create_agent(request: CreateAgentBlueprintRequest):
    usecase = CreateAgentBlueprintUseCase(_repository())
    data = await usecase.execute(request)
    return BaseResponse.ok(data=data, message="에이전트 설계도 생성 성공")


@router.put("/{blueprint_id}")
async def update_agent(blueprint_id: str, request: CreateAgentBlueprintRequest):
    usecase = UpdateAgentBlueprintUseCase(_repository())
    data = await usecase.execute(blueprint_id, request)
    if data is None:
        raise AppException(status_code=404, message="해당 에이전트 설계도를 찾을 수 없습니다.")
    return BaseResponse.ok(data=data, message="에이전트 설계도 수정 성공")


@router.delete("/{blueprint_id}")
async def delete_agent(blueprint_id: str):
    usecase = DeleteAgentBlueprintUseCase(_repository())
    deleted = await usecase.execute(blueprint_id)
    if not deleted:
        raise AppException(status_code=404, message="해당 에이전트 설계도를 찾을 수 없습니다.")
    return BaseResponse.ok(data={"id": blueprint_id}, message="에이전트 설계도 삭제 성공")


@router.get("/{blueprint_id}/download")
async def download_agent(blueprint_id: str):
    """blueprint 로 자립 실행 에이전트 패키지(zip)를 빌드해 다운로드한다."""
    usecase = BuildAgentPackageUseCase(_repository(), _builder())
    built = await usecase.execute(blueprint_id)
    if built is None:
        raise AppException(status_code=404, message="해당 에이전트 설계도를 찾을 수 없습니다.")
    # package_name 은 ASCII 안전 슬러그라 filename 도 ASCII 안전이다.
    headers = {"Content-Disposition": f'attachment; filename="{built.filename}"'}
    return Response(content=built.content, media_type="application/zip", headers=headers)

# HERMES — Claude 노하우 하네스 API
# CLI 스킬(/hermes)과 같은 저장소(~/.claude/hermes)를 읽고 쓴다.

import logging

from fastapi import APIRouter, Query

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.hermes.adapter.outbound.persistence.hermes_file_repository_impl import (
    HermesFileRepositoryImpl,
)
from app.domains.hermes.application.request.create_hermes_entry_request import (
    CreateHermesEntryRequest,
)
from app.domains.hermes.application.request.update_hermes_entry_request import (
    UpdateHermesEntryRequest,
)
from app.domains.hermes.application.usecase.create_hermes_entry_usecase import (
    CreateHermesEntryUseCase,
)
from app.domains.hermes.application.usecase.delete_hermes_entry_usecase import (
    DeleteHermesEntryUseCase,
)
from app.domains.hermes.application.usecase.get_hermes_entry_usecase import GetHermesEntryUseCase
from app.domains.hermes.application.usecase.list_hermes_entries_usecase import (
    ListHermesEntriesUseCase,
)
from app.domains.hermes.application.usecase.update_hermes_entry_usecase import (
    UpdateHermesEntryUseCase,
)
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hermes", tags=["hermes"])


def _repository() -> HermesFileRepositoryImpl:
    return HermesFileRepositoryImpl(get_settings().hermes_store_dir)


@router.get("/entries")
async def list_entries(
    q: str | None = Query(None, description="제목·본문·태그 부분 일치 검색"),
    entry_type: str | None = Query(None, description="memory|tip|workflow|skill|preference"),
    tag: str | None = Query(None),
):
    usecase = ListHermesEntriesUseCase(_repository())
    response = await usecase.execute(query=q, entry_type=entry_type, tag=tag)
    return BaseResponse.ok(data=response, message="헤르메스 노하우 목록 조회 성공")


@router.get("/entries/{entry_id}")
async def get_entry(entry_id: str):
    usecase = GetHermesEntryUseCase(_repository())
    response = await usecase.execute(entry_id)
    if response is None:
        raise AppException(status_code=404, message="해당 노하우를 찾을 수 없습니다.")
    return BaseResponse.ok(data=response, message="헤르메스 노하우 조회 성공")


@router.post("/entries")
async def create_entry(request: CreateHermesEntryRequest):
    usecase = CreateHermesEntryUseCase(_repository())
    response = await usecase.execute(request)
    return BaseResponse.ok(data=response, message="헤르메스 노하우 저장 성공")


@router.put("/entries/{entry_id}")
async def update_entry(entry_id: str, request: UpdateHermesEntryRequest):
    usecase = UpdateHermesEntryUseCase(_repository())
    response = await usecase.execute(entry_id, request)
    if response is None:
        raise AppException(status_code=404, message="해당 노하우를 찾을 수 없습니다.")
    return BaseResponse.ok(data=response, message="헤르메스 노하우 수정 성공")


@router.delete("/entries/{entry_id}")
async def delete_entry(entry_id: str):
    usecase = DeleteHermesEntryUseCase(_repository())
    deleted = await usecase.execute(entry_id)
    if not deleted:
        raise AppException(status_code=404, message="해당 노하우를 찾을 수 없습니다.")
    return BaseResponse.ok(data={"id": entry_id}, message="헤르메스 노하우 삭제 성공")

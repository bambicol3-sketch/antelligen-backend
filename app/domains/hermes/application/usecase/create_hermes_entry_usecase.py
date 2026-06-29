import re
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from app.domains.hermes.application.port.hermes_repository_port import HermesRepositoryPort
from app.domains.hermes.application.request.create_hermes_entry_request import CreateHermesEntryRequest
from app.domains.hermes.application.response.hermes_entry_response import HermesEntryResponse
from app.domains.hermes.domain.entity.hermes_entry import HermesEntry

_KST = ZoneInfo("Asia/Seoul")


def _slugify(title: str) -> str:
    # 한글 포함 단어 문자는 유지, 나머지는 하이픈 — 파일명/URL 안전 슬러그
    slug = re.sub(r"[^\w가-힣]+", "-", title.strip().lower(), flags=re.UNICODE).strip("-")
    return slug[:60] or "entry"


class CreateHermesEntryUseCase:
    def __init__(self, repository: HermesRepositoryPort):
        self._repository = repository

    async def execute(self, request: CreateHermesEntryRequest) -> HermesEntryResponse:
        entry_id = _slugify(request.title)
        if await self._repository.find_by_id(entry_id) is not None:
            entry_id = f"{entry_id}-{uuid.uuid4().hex[:6]}"

        now = datetime.now(_KST)
        entry = HermesEntry(
            id=entry_id,
            title=request.title.strip(),
            type=request.type,
            content=request.content.strip(),
            tags=[t.strip() for t in request.tags if t.strip()],
            project=request.project.strip() or "global",
            source="web",
            created_at=now,
            updated_at=now,
        )
        saved = await self._repository.save(entry)
        return HermesEntryResponse.from_entity(saved)

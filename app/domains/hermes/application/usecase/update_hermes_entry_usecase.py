from datetime import datetime
from zoneinfo import ZoneInfo

from app.domains.hermes.application.port.hermes_repository_port import HermesRepositoryPort
from app.domains.hermes.application.request.update_hermes_entry_request import UpdateHermesEntryRequest
from app.domains.hermes.application.response.hermes_entry_response import HermesEntryResponse

_KST = ZoneInfo("Asia/Seoul")


class UpdateHermesEntryUseCase:
    def __init__(self, repository: HermesRepositoryPort):
        self._repository = repository

    async def execute(
        self, entry_id: str, request: UpdateHermesEntryRequest
    ) -> HermesEntryResponse | None:
        entry = await self._repository.find_by_id(entry_id)
        if entry is None:
            return None

        if request.title is not None:
            entry.title = request.title.strip()
        if request.type is not None:
            entry.type = request.type
        if request.content is not None:
            entry.content = request.content.strip()
        if request.tags is not None:
            entry.tags = [t.strip() for t in request.tags if t.strip()]
        if request.project is not None:
            entry.project = request.project.strip() or "global"
        entry.updated_at = datetime.now(_KST)

        saved = await self._repository.save(entry)
        return HermesEntryResponse.from_entity(saved)

from app.domains.hermes.application.port.hermes_repository_port import HermesRepositoryPort
from app.domains.hermes.application.response.hermes_entry_response import HermesEntryResponse


class GetHermesEntryUseCase:
    def __init__(self, repository: HermesRepositoryPort):
        self._repository = repository

    async def execute(self, entry_id: str) -> HermesEntryResponse | None:
        entry = await self._repository.find_by_id(entry_id)
        if entry is None:
            return None
        return HermesEntryResponse.from_entity(entry)

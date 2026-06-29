from app.domains.hermes.application.port.hermes_repository_port import HermesRepositoryPort


class DeleteHermesEntryUseCase:
    def __init__(self, repository: HermesRepositoryPort):
        self._repository = repository

    async def execute(self, entry_id: str) -> bool:
        return await self._repository.delete(entry_id)

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from app.domains.hermes.application.port.agent_blueprint_repository_port import (
    AgentBlueprintRepositoryPort,
)
from app.domains.hermes.application.port.agent_package_parser_port import (
    AgentPackageParserPort,
)
from app.domains.hermes.application.response.agent_blueprint_response import (
    AgentBlueprintResponse,
)

_KST = ZoneInfo("Asia/Seoul")


class ImportAgentPackageUseCase:
    """다른 PC 에서 다운로드한 에이전트 패키지(zip)를 업로드받아 blueprint 를 복원/등록한다.

    복원 후 이 백엔드의 에이전트 목록에 나타나며, /download 로 새 PC 에서 다시 받아
    `python agent_main.py` 로 실행할 수 있다.
    """

    def __init__(
        self,
        repository: AgentBlueprintRepositoryPort,
        parser: AgentPackageParserPort,
    ):
        self._repository = repository
        self._parser = parser

    async def execute(
        self, content: bytes, *, new_owner: str | None = None
    ) -> AgentBlueprintResponse | None:
        blueprint = self._parser.parse(content)
        if blueprint is None:
            return None

        now = datetime.now(_KST)
        # 원본 id 가 이미 존재하면 충돌을 피해 새 id 로 사본을 만든다(restore-as-copy).
        if not blueprint.id or await self._repository.find_by_id(blueprint.id) is not None:
            blueprint.id = uuid.uuid4().hex[:12]
            blueprint.created_at = now
        elif blueprint.created_at is None:
            blueprint.created_at = now
        if new_owner:
            blueprint.owner = new_owner
        blueprint.updated_at = now

        saved = await self._repository.save(blueprint)
        return AgentBlueprintResponse.from_entity(saved)

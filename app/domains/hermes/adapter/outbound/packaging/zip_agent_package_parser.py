# 업로드된 에이전트 패키지(zip) → AgentBlueprint 복원. ZipAgentPackageBuilder 의 역방향.
# 패키지 루트의 .hermes/blueprint.json manifest 를 찾아 엔티티로 되돌린다.

import io
import json
import logging
import zipfile

from app.domains.hermes.adapter.outbound.packaging.zip_agent_package_builder import (
    BLUEPRINT_MANIFEST_PATH,
)
from app.domains.hermes.application.port.agent_package_parser_port import (
    AgentPackageParserPort,
)
from app.domains.hermes.domain.entity.agent_blueprint import AgentBlueprint
from app.domains.hermes.infrastructure.mapper.agent_blueprint_mapper import (
    AgentBlueprintMapper,
)

logger = logging.getLogger(__name__)

# zip 폭탄 방어용 상한(압축 해제 후 manifest 크기). manifest 는 작은 JSON 이라 넉넉히 잡아도 충분.
_MAX_MANIFEST_BYTES = 1_000_000


class ZipAgentPackageParser(AgentPackageParserPort):
    def parse(self, content: bytes) -> AgentBlueprint | None:
        try:
            zf = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile:
            logger.warning("agent package import: not a valid zip")
            return None

        with zf:
            manifest_name = self._find_manifest(zf)
            if manifest_name is None:
                logger.warning("agent package import: blueprint manifest not found")
                return None
            info = zf.getinfo(manifest_name)
            if info.file_size > _MAX_MANIFEST_BYTES:
                logger.warning("agent package import: manifest too large (%d)", info.file_size)
                return None
            try:
                data = json.loads(zf.read(manifest_name).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                logger.warning("agent package import: manifest parse failed: %s", e)
                return None

        if not isinstance(data, dict) or not data.get("id"):
            logger.warning("agent package import: manifest missing required fields")
            return None
        return AgentBlueprintMapper.to_entity(data)

    @staticmethod
    def _find_manifest(zf: zipfile.ZipFile) -> str | None:
        """패키지 루트 디렉터리명에 무관하게 .hermes/blueprint.json 으로 끝나는 항목을 찾는다."""
        for name in zf.namelist():
            if name.endswith(BLUEPRINT_MANIFEST_PATH):
                return name
        return None

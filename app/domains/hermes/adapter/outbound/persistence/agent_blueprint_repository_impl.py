# 파일 기반 저장소 — 기존 hermes(entries)와 동일한 패턴.
# <store_dir>/<id>.json 1파일 = AgentBlueprint 1건.

import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.domains.hermes.application.port.agent_blueprint_repository_port import (
    AgentBlueprintRepositoryPort,
)
from app.domains.hermes.domain.entity.agent_blueprint import AgentBlueprint
from app.domains.hermes.infrastructure.mapper.agent_blueprint_mapper import (
    AgentBlueprintMapper,
)

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")
_EPOCH = datetime.min.replace(tzinfo=_KST)


class AgentBlueprintRepositoryImpl(AgentBlueprintRepositoryPort):
    def __init__(self, store_dir: str):
        self._dir = Path(store_dir).expanduser()
        self._dir.mkdir(parents=True, exist_ok=True)

    async def find_all(self, owner: str | None = None) -> list[AgentBlueprint]:
        items: list[AgentBlueprint] = []
        for path in self._dir.glob("*.json"):
            entity = self._read(path)
            if entity is None:
                continue
            if owner is not None and entity.owner != owner:
                continue
            items.append(entity)
        items.sort(key=lambda e: e.updated_at or e.created_at or _EPOCH, reverse=True)
        return items

    async def find_by_id(self, blueprint_id: str) -> AgentBlueprint | None:
        path = self._path(blueprint_id)
        if not path.is_file():
            return None
        return self._read(path)

    async def save(self, blueprint: AgentBlueprint) -> AgentBlueprint:
        path = self._path(blueprint.id)
        data = AgentBlueprintMapper.to_dict(blueprint)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return blueprint

    async def delete(self, blueprint_id: str) -> bool:
        path = self._path(blueprint_id)
        if not path.is_file():
            return False
        path.unlink()
        return True

    # ── 내부 ──────────────────────────────────────────────────────────
    def _path(self, blueprint_id: str) -> Path:
        safe_id = Path(blueprint_id).name  # 경로 탈출 방지
        return self._dir / f"{safe_id}.json"

    def _read(self, path: Path) -> AgentBlueprint | None:
        try:
            return AgentBlueprintMapper.to_entity(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.warning("agent blueprint read failed [%s]: %s", path.name, e)
            return None

# 파일 기반 저장소 — ~/.claude/hermes/ 를 CLI 스킬(/hermes)과 공유한다.
# entries/<id>.md 1파일 = 노하우 1건, INDEX.md 는 쓰기 때마다 전체 재생성.

import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.domains.hermes.application.port.hermes_repository_port import HermesRepositoryPort
from app.domains.hermes.domain.entity.hermes_entry import HermesEntry
from app.domains.hermes.infrastructure.mapper.hermes_entry_mapper import HermesEntryMapper

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")
_EPOCH = datetime.min.replace(tzinfo=_KST)


class HermesFileRepositoryImpl(HermesRepositoryPort):
    def __init__(self, store_dir: str):
        self._store_dir = Path(store_dir).expanduser()
        self._entries_dir = self._store_dir / "entries"
        self._index_path = self._store_dir / "INDEX.md"
        self._entries_dir.mkdir(parents=True, exist_ok=True)

    async def find_all(self) -> list[HermesEntry]:
        entries: list[HermesEntry] = []
        for path in self._entries_dir.glob("*.md"):
            entry = self._read_entry(path)
            if entry is not None:
                entries.append(entry)
        entries.sort(key=lambda e: e.updated_at or e.created_at or _EPOCH, reverse=True)
        return entries

    async def find_by_id(self, entry_id: str) -> HermesEntry | None:
        path = self._entry_path(entry_id)
        if not path.is_file():
            return None
        return self._read_entry(path)

    async def save(self, entry: HermesEntry) -> HermesEntry:
        path = self._entry_path(entry.id)
        path.write_text(HermesEntryMapper.to_markdown(entry), encoding="utf-8")
        await self._rebuild_index()
        return entry

    async def delete(self, entry_id: str) -> bool:
        path = self._entry_path(entry_id)
        if not path.is_file():
            return False
        path.unlink()
        await self._rebuild_index()
        return True

    # ── 내부 ──────────────────────────────────────────────────────────

    def _entry_path(self, entry_id: str) -> Path:
        # 경로 탈출 방지 — id 는 슬러그만 허용
        safe_id = Path(entry_id).name
        return self._entries_dir / f"{safe_id}.md"

    def _read_entry(self, path: Path) -> HermesEntry | None:
        try:
            raw = path.read_text(encoding="utf-8")
            return HermesEntryMapper.to_entity(path.stem, raw)
        except OSError as e:
            logger.warning("hermes entry read failed [%s]: %s", path.name, e)
            return None

    async def _rebuild_index(self) -> None:
        """INDEX.md 전체 재생성 — CLI 스킬과 동일 포맷 (SKILL.md 스펙 참조)."""
        entries = await self.find_all()
        lines = [
            "# Hermes Index",
            "",
            "<!-- 이 파일은 자동 생성됩니다 (entries/ 스캔으로 재생성). 직접 편집하지 마세요. -->",
            "",
            f"총 {len(entries)}개 · 마지막 갱신: {datetime.now(_KST).isoformat(timespec='seconds')}",
            "",
        ]
        for e in entries:
            tags = " ".join(f"#{t}" for t in e.tags)
            tags_part = f" {tags}" if tags else ""
            lines.append(f"- [{e.type.value}] **{e.title}** (`{e.id}`){tags_part} — {e.summary()}")
        self._index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

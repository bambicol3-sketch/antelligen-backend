# 엔트리 마크다운 파일(YAML frontmatter + 본문) ↔ Domain Entity 변환.
# 파일 포맷은 CLI 스킬(~/.claude/skills/hermes/SKILL.md)과 공유되는 고정 스펙이므로
# 형식을 바꾸려면 SKILL.md 도 함께 수정해야 한다.

from datetime import datetime

import yaml

from app.domains.hermes.domain.entity.hermes_entry import HermesEntry
from app.domains.hermes.domain.value_object.entry_type import HermesEntryType


def _parse_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


class HermesEntryMapper:
    @staticmethod
    def to_entity(entry_id: str, raw_text: str) -> HermesEntry:
        meta: dict = {}
        content = raw_text

        if raw_text.startswith("---"):
            parts = raw_text.split("---", 2)
            if len(parts) >= 3:
                try:
                    meta = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    meta = {}
                content = parts[2]

        try:
            entry_type = HermesEntryType(str(meta.get("type", "tip")))
        except ValueError:
            entry_type = HermesEntryType.TIP

        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        return HermesEntry(
            id=str(meta.get("id", entry_id)),
            title=str(meta.get("title", entry_id)),
            type=entry_type,
            content=content.strip(),
            tags=[str(t) for t in tags],
            project=str(meta.get("project", "global")),
            source=str(meta.get("source", "cli")),
            created_at=_parse_datetime(meta.get("created_at")),
            updated_at=_parse_datetime(meta.get("updated_at")),
        )

    @staticmethod
    def to_markdown(entry: HermesEntry) -> str:
        # yaml.safe_dump 는 한글을 escape 하므로 단순 키-값은 직접 직렬화한다.
        tags = ", ".join(entry.tags)
        created = entry.created_at.isoformat() if entry.created_at else ""
        updated = entry.updated_at.isoformat() if entry.updated_at else ""
        frontmatter = (
            f"---\n"
            f"id: {entry.id}\n"
            f"title: {_quote(entry.title)}\n"
            f"type: {entry.type.value}\n"
            f"tags: [{tags}]\n"
            f"project: {entry.project}\n"
            f"source: {entry.source}\n"
            f"created_at: {created}\n"
            f"updated_at: {updated}\n"
            f"---\n"
        )
        return f"{frontmatter}\n{entry.content.strip()}\n"


def _quote(value: str) -> str:
    # 콜론/따옴표가 들어간 제목이 YAML 파싱을 깨지 않도록 쌍따옴표로 감싼다.
    if any(ch in value for ch in ':#"[]{}'):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value

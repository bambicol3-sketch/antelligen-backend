from enum import Enum


class HermesEntryType(str, Enum):
    """노하우 분류 — CLI 스킬(~/.claude/skills/hermes)과 공유되는 고정 값."""

    MEMORY = "memory"          # 사실 / 컨텍스트
    TIP = "tip"                # 편의 팁
    WORKFLOW = "workflow"      # 작업 절차
    SKILL = "skill"            # 명령 / 도구 노하우
    PREFERENCE = "preference"  # 사용자 선호 / 스타일

from typing import List

from app.domains.ddakjubu.domain.entity.learning_note import LearningNote


class LearningNoteMarkdownFormatter:
    """LearningNote 도메인 객체를 ddakjubu.md에 기록 가능한 Markdown 문자열로 변환한다."""

    HEADER_TITLE = "# 딱주부 학습 노트"
    HEADER_DESC = (
        "딱주부TV(UC2-YdiOkgqWzIdDwCYW1utw)의 '학습프로그램' 중 "
        "'back to the basic' / '리듬 시리즈' 영상 학습 결과를 누적 기록한다."
    )

    def format_header(self) -> str:
        return f"{self.HEADER_TITLE}\n\n{self.HEADER_DESC}\n"

    def format_notes(self, notes: List[LearningNote]) -> str:
        if not notes:
            return ""
        blocks = [self._format_single_note(note) for note in notes]
        return "\n".join(blocks)

    def _format_single_note(self, note: LearningNote) -> str:
        published = note.published_at.strftime("%Y-%m-%d")
        learned = note.learned_at.strftime("%Y-%m-%d %H:%M")

        lines: List[str] = []
        lines.append(f"## [{note.program_category}] {note.video_title}")
        lines.append("")
        lines.append(f"- video_id: `{note.video_id}`")
        lines.append(f"- 채널: {note.channel_name}")
        lines.append(f"- 업로드일: {published}")
        lines.append(f"- 학습일시: {learned}")
        lines.append("")
        lines.append("### 핵심 요약")
        lines.append(note.summary.strip() or "-")
        lines.append("")

        if note.stock_insights:
            lines.append("### 종목별 인사이트")
            for insight in note.stock_insights:
                lines.append(
                    f"#### {insight.stock_name}"
                    + (f" ({insight.ticker})" if insight.ticker else "")
                )
                lines.append(f"- 투자 관점: {insight.investment_view or '-'}")
                if insight.key_claims:
                    lines.append("- 핵심 주장:")
                    for claim in insight.key_claims:
                        lines.append(f"  - {claim}")
                if insight.supporting_evidence:
                    lines.append("- 근거:")
                    for evidence in insight.supporting_evidence:
                        lines.append(f"  - {evidence}")
                lines.append("")

        lines.append("---")
        lines.append("")
        return "\n".join(lines)

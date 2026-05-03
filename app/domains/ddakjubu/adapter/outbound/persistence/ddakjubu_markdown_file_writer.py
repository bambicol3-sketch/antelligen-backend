import logging
import re
from pathlib import Path
from typing import List, Set

from app.domains.ddakjubu.application.port.ddakjubu_note_writer_port import DdakjubuNoteWriterPort
from app.domains.ddakjubu.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu.domain.service.learning_note_markdown_formatter import (
    LearningNoteMarkdownFormatter,
)

logger = logging.getLogger(__name__)

VIDEO_ID_PATTERN = re.compile(r"video_id:\s*`([^`]+)`")


class DdakjubuMarkdownFileWriter(DdakjubuNoteWriterPort):
    """ddakjubu.md 파일에 학습 노트를 누적 기록하는 파일 어댑터."""

    def __init__(self, file_path: str):
        self._path = Path(file_path)
        self._formatter = LearningNoteMarkdownFormatter()

    def load_existing_video_ids(self) -> Set[str]:
        if not self._path.exists():
            return set()
        try:
            content = self._path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("[ddakjubu_file] 기존 파일 읽기 실패: %s", e)
            return set()
        return set(VIDEO_ID_PATTERN.findall(content))

    def append_notes(self, notes: List[LearningNote]) -> str:
        if not notes:
            return str(self._path.resolve())

        self._path.parent.mkdir(parents=True, exist_ok=True)

        if not self._path.exists() or self._path.stat().st_size == 0:
            initial = self._formatter.format_header() + "\n"
            self._path.write_text(initial, encoding="utf-8")

        body = self._formatter.format_notes(notes)
        with self._path.open("a", encoding="utf-8") as fp:
            if not body.startswith("\n"):
                fp.write("\n")
            fp.write(body)
            if not body.endswith("\n"):
                fp.write("\n")

        resolved = str(self._path.resolve())
        logger.info(
            "[ddakjubu_file] 학습 노트 저장 완료 path=%s appended_count=%d",
            resolved,
            len(notes),
        )
        return resolved

from abc import ABC, abstractmethod
from typing import List, Set

from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote


class Ddakjubu2NoteWriterPort(ABC):
    """학습 결과(LearningNote) 를 ddakjubu2.md 파일에 저장하는 포트."""

    @abstractmethod
    def load_existing_video_ids(self) -> Set[str]:
        """기존 파일에 이미 기록된 video_id 목록을 반환한다.

        파일이 없으면 빈 집합을 반환한다.
        """
        raise NotImplementedError

    @abstractmethod
    def append_notes(self, notes: List[LearningNote]) -> str:
        """신규 학습 결과를 파일에 누적 기록하고 저장된 파일 경로를 반환한다."""
        raise NotImplementedError

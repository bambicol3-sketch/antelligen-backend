from abc import ABC, abstractmethod

from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu2.domain.entity.source_video import SourceVideo


class VideoLearningPort(ABC):
    """영상 데이터로부터 주식 종목, 투자 관점, 핵심 주장, 근거를 학습 및 추출하는 포트."""

    @abstractmethod
    async def learn(self, source_video: SourceVideo) -> LearningNote:
        raise NotImplementedError

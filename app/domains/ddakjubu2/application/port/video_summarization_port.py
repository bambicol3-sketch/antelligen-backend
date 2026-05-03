from abc import ABC, abstractmethod

from app.domains.ddakjubu2.domain.entity.source_video import SourceVideo


class VideoSummarizationPort(ABC):
    """영상 자막·제목·설명을 기반으로 유튜브 프리미엄 요약 수준의 핵심 요약을 생성하는 포트.

    2-pass 학습 파이프라인의 1차 패스에 해당한다.
    반환 값은 자연어 문단 형태의 핵심 요약 문자열이다.
    """

    @abstractmethod
    async def summarize(self, source_video: SourceVideo) -> str:
        raise NotImplementedError

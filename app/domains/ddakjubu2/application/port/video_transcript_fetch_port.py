from abc import ABC, abstractmethod
from typing import List, Optional


class VideoTranscriptFetchPort(ABC):
    """유튜브 영상 자막(스크립트) 추출 포트."""

    @abstractmethod
    async def fetch_transcript(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> str:
        """주어진 video_id 의 자막 텍스트를 반환한다.

        자막이 없거나 추출 실패 시 빈 문자열을 반환한다.
        """
        raise NotImplementedError

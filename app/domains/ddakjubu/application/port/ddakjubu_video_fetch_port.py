from abc import ABC, abstractmethod
from typing import List

from app.domains.ddakjubu.domain.entity.source_video import SourceVideo


class DdakjubuVideoFetchPort(ABC):
    """딱주부TV '학습프로그램' 카테고리의 학습 대상 영상을 수집하는 포트."""

    @abstractmethod
    async def fetch_learning_videos(
        self,
        channel_ids: List[str],
        program_filters: List[str],
        max_results_per_channel: int = 20,
    ) -> List[SourceVideo]:
        """주어진 채널 목록에서 program_filters 키워드에 해당하는 학습 영상을 반환한다.

        channel_ids가 비어 있으면 영상 조회를 수행하지 않고 빈 리스트를 반환한다.
        영상이 존재하지 않는 경우에도 빈 리스트를 반환한다.
        """
        raise NotImplementedError

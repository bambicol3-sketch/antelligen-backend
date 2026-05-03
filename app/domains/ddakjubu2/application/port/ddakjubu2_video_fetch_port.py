from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from app.domains.ddakjubu2.domain.entity.source_video import SourceVideo


class Ddakjubu2VideoFetchPort(ABC):
    """딱주부TV 채널의 모든 주식 관련 영상을 수집하는 포트."""

    @abstractmethod
    async def fetch_channel_videos(
        self,
        channel_ids: List[str],
        published_after: Optional[datetime] = None,
    ) -> List[SourceVideo]:
        """주어진 채널 목록에서 업로드된 영상을 반환한다.

        published_after 가 지정되면 해당 일시 이후에 업로드된 영상만 수집한다.
        channel_ids 가 비어 있으면 영상 조회를 수행하지 않고 빈 리스트를 반환한다.
        영상이 존재하지 않는 경우에도 빈 리스트를 반환한다.
        """
        raise NotImplementedError

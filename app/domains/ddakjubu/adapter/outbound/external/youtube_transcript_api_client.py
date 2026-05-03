import asyncio
import logging
from typing import List, Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from app.domains.ddakjubu.application.port.video_transcript_fetch_port import (
    VideoTranscriptFetchPort,
)

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGES: List[str] = ["ko", "ko-KR", "en", "en-US"]


class YoutubeTranscriptApiClient(VideoTranscriptFetchPort):
    """youtube-transcript-api 라이브러리를 이용해 영상 자막을 추출하는 어댑터."""

    def __init__(self):
        self._api = YouTubeTranscriptApi()

    async def fetch_transcript(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> str:
        lang_list = languages or DEFAULT_LANGUAGES
        try:
            fetched = await asyncio.to_thread(
                self._api.fetch,
                video_id,
                lang_list,
            )
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
            logger.info(
                "[ddakjubu_transcript] 자막 없음 video_id=%s reason=%s",
                video_id,
                type(e).__name__,
            )
            return ""
        except Exception as e:
            logger.warning(
                "[ddakjubu_transcript] 자막 추출 실패 video_id=%s error=%s",
                video_id,
                e,
            )
            return ""

        return " ".join(
            snippet.text.strip()
            for snippet in fetched
            if getattr(snippet, "text", "")
        ).strip()

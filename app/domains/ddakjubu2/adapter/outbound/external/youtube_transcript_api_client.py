import asyncio
import random
from typing import List, Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)
from youtube_transcript_api.proxies import (
    GenericProxyConfig,
    ProxyConfig,
    WebshareProxyConfig,
)

from app.domains.ddakjubu2.application.port.video_transcript_fetch_port import (
    VideoTranscriptFetchPort,
)

DEFAULT_LANGUAGES: List[str] = ["ko", "ko-KR", "en", "en-US"]

DEFAULT_MAX_RETRIES = 10
DEFAULT_RETRY_DELAY_RANGE_SECONDS = (2.0, 5.0)


def build_proxy_config_from_settings(settings) -> Optional[ProxyConfig]:
    """Settings 로부터 proxy 설정을 조립한다.

    우선순위: Webshare → Generic HTTP/HTTPS → None(직결)
    설정이 없으면 None 을 반환해 기존 직결 방식으로 동작한다.
    """
    webshare_user = getattr(settings, "youtube_proxy_webshare_username", "")
    webshare_pass = getattr(settings, "youtube_proxy_webshare_password", "")
    if webshare_user and webshare_pass:
        print("[ddakjubu2_transcript] Webshare 프록시 사용")
        return WebshareProxyConfig(
            proxy_username=webshare_user,
            proxy_password=webshare_pass,
        )

    http_url = getattr(settings, "youtube_proxy_http_url", "")
    https_url = getattr(settings, "youtube_proxy_https_url", "")
    if http_url or https_url:
        print(
            f"[ddakjubu2_transcript] Generic 프록시 사용 "
            f"http={'설정됨' if http_url else '없음'} "
            f"https={'설정됨' if https_url else '없음'}"
        )
        return GenericProxyConfig(
            http_url=http_url or None,
            https_url=https_url or None,
        )

    print("[ddakjubu2_transcript] 프록시 미설정 - 직결로 동작 (IP 차단 시 자막 추출 실패)")
    return None


class YoutubeTranscriptApiClient(VideoTranscriptFetchPort):
    """youtube-transcript-api 라이브러리를 이용해 영상 자막을 추출하는 어댑터.

    proxy_config 가 주어지면 해당 프록시를 통해 요청해 IP 차단을 우회한다.
    429/네트워크 에러에 대해 최대 max_retries 회 재시도하며, 재시도 사이에
    랜덤 딜레이를 두어 회전 프록시의 다른 IP 로 요청이 분산되도록 유도한다.
    """

    def __init__(
        self,
        proxy_config: Optional[ProxyConfig] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay_range_seconds: tuple = DEFAULT_RETRY_DELAY_RANGE_SECONDS,
    ):
        self._api = YouTubeTranscriptApi(proxy_config=proxy_config)
        self._max_retries = max_retries
        self._retry_delay_range = retry_delay_range_seconds

    async def fetch_transcript(
        self,
        video_id: str,
        languages: Optional[List[str]] = None,
    ) -> str:
        lang_list = languages or DEFAULT_LANGUAGES

        for attempt in range(1, self._max_retries + 1):
            try:
                fetched = await asyncio.to_thread(
                    self._api.fetch,
                    video_id,
                    lang_list,
                )
            except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
                # 자막 자체가 없는 케이스는 재시도해도 결과 동일 → 즉시 종료
                print(
                    f"[ddakjubu2_transcript] 자막 없음 video_id={video_id} "
                    f"reason={type(e).__name__}"
                )
                return ""
            except Exception as e:
                error_snippet = str(e).split("\n")[0][:160]
                if attempt < self._max_retries:
                    delay = random.uniform(*self._retry_delay_range)
                    print(
                        f"[ddakjubu2_transcript] 시도 {attempt}/{self._max_retries} 실패 "
                        f"video_id={video_id} error={error_snippet} → {delay:.1f}s 후 재시도",
                        flush=True,
                    )
                    await asyncio.sleep(delay)
                    continue
                print(
                    f"[ddakjubu2_transcript] 최종 실패 "
                    f"video_id={video_id} attempts={self._max_retries} "
                    f"error={error_snippet}",
                    flush=True,
                )
                return ""

            text = " ".join(
                snippet.text.strip()
                for snippet in fetched
                if getattr(snippet, "text", "")
            ).strip()
            print(
                f"[ddakjubu2_transcript] 자막 추출 성공 video_id={video_id} "
                f"attempt={attempt} length={len(text)}",
                flush=True,
            )
            return text

        return ""

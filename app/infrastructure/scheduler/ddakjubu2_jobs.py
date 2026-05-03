import logging
import time as _time

from app.domains.ddakjubu2.adapter.outbound.external.openai_video_learning_client import (
    OpenAIVideoLearningClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.openai_video_summarization_client import (
    OpenAIVideoSummarizationClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.youtube_ddakjubu2_video_client import (
    YoutubeDdakjubu2VideoClient,
)
from app.domains.ddakjubu2.adapter.outbound.persistence.ddakjubu2_markdown_file_writer import (
    Ddakjubu2MarkdownFileWriter,
)
from app.domains.ddakjubu2.application.usecase.learn_ddakjubu2_videos_usecase import (
    LearnDdakjubu2VideosUseCase,
)
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


async def job_learn_ddakjubu2_videos():
    """Daily 05:00 KST: 딱주부TV 채널의 최근 추가된 영상을 학습해 ddakjubu2.md 에 업데이트."""
    start = _time.monotonic()
    print("[Scheduler][Ddakjubu2] 매일 05:00 KST 학습 job 시작", flush=True)
    logger.info("[Scheduler][Ddakjubu2] Starting daily learning job")

    try:
        settings = get_settings()

        video_fetch_port = YoutubeDdakjubu2VideoClient(api_key=settings.youtube_api_key)
        video_summarization_port = OpenAIVideoSummarizationClient(
            api_key=settings.openai_api_key,
            model=settings.ddakjubu2_llm_model,
        )
        video_learning_port = OpenAIVideoLearningClient(
            api_key=settings.openai_api_key,
            model=settings.ddakjubu2_llm_model,
        )
        note_writer_port = Ddakjubu2MarkdownFileWriter(
            file_path=settings.ddakjubu2_md_path
        )

        usecase = LearnDdakjubu2VideosUseCase(
            video_fetch_port=video_fetch_port,
            video_summarization_port=video_summarization_port,
            video_learning_port=video_learning_port,
            note_writer_port=note_writer_port,
        )

        result = await usecase.execute()

        elapsed = _time.monotonic() - start
        print(
            f"[Scheduler][Ddakjubu2] 완료 file_path={result.file_path} "
            f"processed={result.processed_count} "
            f"skipped_duplicates={result.skipped_duplicate_count} "
            f"elapsed={elapsed:.1f}s",
            flush=True,
        )
        logger.info(
            "[Scheduler][Ddakjubu2] Complete — file_path=%s, processed=%d, "
            "skipped_duplicates=%d (%.1fs)",
            result.file_path,
            result.processed_count,
            result.skipped_duplicate_count,
            elapsed,
        )
    except Exception as e:
        elapsed = _time.monotonic() - start
        print(
            f"[Scheduler][Ddakjubu2] 실패 elapsed={elapsed:.1f}s error={e}",
            flush=True,
        )
        logger.error(
            "[Scheduler][Ddakjubu2] Failed after %.1fs: %s", elapsed, str(e)
        )

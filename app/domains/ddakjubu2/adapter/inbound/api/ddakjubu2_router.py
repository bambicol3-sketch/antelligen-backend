import asyncio
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks

from app.common.response.base_response import BaseResponse
from app.domains.ddakjubu2.adapter.outbound.external.openai_video_learning_client import (
    OpenAIVideoLearningClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.openai_video_summarization_client import (
    OpenAIVideoSummarizationClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.youtube_ddakjubu2_video_client import (
    YoutubeDdakjubu2VideoClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.youtube_transcript_api_client import (
    YoutubeTranscriptApiClient,
    build_proxy_config_from_settings,
)
from app.domains.ddakjubu2.adapter.outbound.persistence.ddakjubu2_markdown_file_writer import (
    Ddakjubu2MarkdownFileWriter,
)
from app.domains.ddakjubu2.application.usecase.enhance_ddakjubu2_videos_usecase import (
    EnhanceDdakjubu2VideosUseCase,
)
from app.domains.ddakjubu2.application.usecase.learn_ddakjubu2_videos_usecase import (
    LearnDdakjubu2VideosUseCase,
)
from app.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/ddakjubu2", tags=["ddakjubu2"])


@router.post("/learn")
async def learn_ddakjubu2_videos():
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
    note_writer_port = Ddakjubu2MarkdownFileWriter(file_path=settings.ddakjubu2_md_path)

    usecase = LearnDdakjubu2VideosUseCase(
        video_fetch_port=video_fetch_port,
        video_summarization_port=video_summarization_port,
        video_learning_port=video_learning_port,
        note_writer_port=note_writer_port,
    )
    response = await usecase.execute()

    return BaseResponse.ok(data=response, message="딱주부2 학습 노트 저장 완료")


@router.post("/enhance")
async def enhance_ddakjubu2_videos(background_tasks: BackgroundTasks):
    """2026년 업로드 영상을 자막 포함으로 재학습하여 별도 파일에 저장한다.

    10분/영상 페이스로 진행되어 수 시간이 걸리므로 HTTP 응답은 즉시 반환하고
    실제 파이프라인은 백그라운드로 실행된다.
    """
    settings = get_settings()

    video_fetch_port = YoutubeDdakjubu2VideoClient(api_key=settings.youtube_api_key)
    transcript_fetch_port = YoutubeTranscriptApiClient(
        proxy_config=build_proxy_config_from_settings(settings)
    )
    video_summarization_port = OpenAIVideoSummarizationClient(
        api_key=settings.openai_api_key,
        model=settings.ddakjubu2_llm_model,
    )
    video_learning_port = OpenAIVideoLearningClient(
        api_key=settings.openai_api_key,
        model=settings.ddakjubu2_llm_model,
    )
    note_writer_port = Ddakjubu2MarkdownFileWriter(
        file_path=settings.ddakjubu2_enhanced_md_path
    )

    published_after = datetime.fromisoformat(
        settings.ddakjubu2_enhance_published_after_iso
    )

    usecase = EnhanceDdakjubu2VideosUseCase(
        video_fetch_port=video_fetch_port,
        transcript_fetch_port=transcript_fetch_port,
        video_summarization_port=video_summarization_port,
        video_learning_port=video_learning_port,
        note_writer_port=note_writer_port,
        published_after=published_after,
        sleep_between_videos_seconds=settings.ddakjubu2_enhance_sleep_seconds,
    )

    background_tasks.add_task(_run_enhance_in_background, usecase)

    return BaseResponse.ok(
        data={
            "status": "started",
            "file_path": settings.ddakjubu2_enhanced_md_path,
            "sleep_between_videos_seconds": settings.ddakjubu2_enhance_sleep_seconds,
            "published_after": settings.ddakjubu2_enhance_published_after_iso,
        },
        message="딱주부2 자막 포함 재학습이 백그라운드로 시작됐습니다",
    )


async def _run_enhance_in_background(usecase: EnhanceDdakjubu2VideosUseCase) -> None:
    try:
        await usecase.execute()
    except asyncio.CancelledError:
        print("[ddakjubu2_enhance] 백그라운드 작업이 취소됐습니다", flush=True)
        raise
    except Exception as e:
        print(f"[ddakjubu2_enhance] 백그라운드 작업 실패: {e}", flush=True)

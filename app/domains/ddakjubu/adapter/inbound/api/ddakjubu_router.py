from fastapi import APIRouter

from app.common.response.base_response import BaseResponse
from app.domains.ddakjubu.adapter.outbound.external.openai_video_learning_client import (
    OpenAIVideoLearningClient,
)
from app.domains.ddakjubu.adapter.outbound.external.openai_video_summarization_client import (
    OpenAIVideoSummarizationClient,
)
from app.domains.ddakjubu.adapter.outbound.external.youtube_ddakjubu_video_client import (
    YoutubeDdakjubuVideoClient,
)
from app.domains.ddakjubu.adapter.outbound.external.youtube_transcript_api_client import (
    YoutubeTranscriptApiClient,
)
from app.domains.ddakjubu.adapter.outbound.persistence.ddakjubu_markdown_file_writer import (
    DdakjubuMarkdownFileWriter,
)
from app.domains.ddakjubu.application.usecase.learn_ddakjubu_videos_usecase import (
    LearnDdakjubuVideosUseCase,
)
from app.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/ddakjubu", tags=["ddakjubu"])


@router.post("/learn")
async def learn_ddakjubu_videos():
    settings = get_settings()

    video_fetch_port = YoutubeDdakjubuVideoClient(api_key=settings.youtube_api_key)
    transcript_fetch_port = YoutubeTranscriptApiClient()
    video_summarization_port = OpenAIVideoSummarizationClient(
        api_key=settings.openai_api_key,
        model=settings.ddakjubu_llm_model,
    )
    video_learning_port = OpenAIVideoLearningClient(
        api_key=settings.openai_api_key,
        model=settings.ddakjubu_llm_model,
    )
    note_writer_port = DdakjubuMarkdownFileWriter(file_path=settings.ddakjubu_md_path)

    usecase = LearnDdakjubuVideosUseCase(
        video_fetch_port=video_fetch_port,
        transcript_fetch_port=transcript_fetch_port,
        video_summarization_port=video_summarization_port,
        video_learning_port=video_learning_port,
        note_writer_port=note_writer_port,
    )
    response = await usecase.execute()

    return BaseResponse.ok(data=response, message="딱주부 학습 노트 저장 완료")

from datetime import datetime, timezone
from typing import List

from app.domains.ddakjubu2.application.port.ddakjubu2_note_writer_port import (
    Ddakjubu2NoteWriterPort,
)
from app.domains.ddakjubu2.application.port.ddakjubu2_video_fetch_port import (
    Ddakjubu2VideoFetchPort,
)
from app.domains.ddakjubu2.application.port.video_learning_port import VideoLearningPort
from app.domains.ddakjubu2.application.port.video_summarization_port import (
    VideoSummarizationPort,
)
from app.domains.ddakjubu2.application.response.learn_ddakjubu2_response import (
    LearnDdakjubu2Response,
    LearnedVideoItem,
)
from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu2.domain.entity.source_video import SourceVideo

DDAKJUBU2_CHANNEL_IDS: List[str] = [
    "UC2-YdiOkgqWzIdDwCYW1utw",  # 딱딱한 주식 부드럽게 | 딱주부TV
]

# 수집 하한 일시: 2024-06-09 이후 업로드된 영상만 학습 대상
DDAKJUBU2_PUBLISHED_AFTER = datetime(2024, 6, 9, 0, 0, 0, tzinfo=timezone.utc)

# 배치 저장 크기: N개마다 파일 flush 하여 장시간 실행 중 OpenAI 장애/중단 시 진행분 보존
BATCH_SAVE_SIZE = 10


class LearnDdakjubu2VideosUseCase:
    """딱주부TV 채널의 모든 영상을 LLM 으로 학습하고 ddakjubu2.md 에 저장한다."""

    def __init__(
        self,
        video_fetch_port: Ddakjubu2VideoFetchPort,
        video_summarization_port: VideoSummarizationPort,
        video_learning_port: VideoLearningPort,
        note_writer_port: Ddakjubu2NoteWriterPort,
    ):
        self._video_fetch_port = video_fetch_port
        self._video_summarization_port = video_summarization_port
        self._video_learning_port = video_learning_port
        self._note_writer_port = note_writer_port

    async def execute(self) -> LearnDdakjubu2Response:
        print("[ddakjubu2] 학습 파이프라인 시작")

        if not DDAKJUBU2_CHANNEL_IDS:
            print("[ddakjubu2] 채널 목록이 비어있어 영상 조회를 수행하지 않습니다.")
            return LearnDdakjubu2Response(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=0,
                videos=[],
            )

        print(
            f"[ddakjubu2] 영상 조회 요청 생성: channels={DDAKJUBU2_CHANNEL_IDS}, "
            f"published_after={DDAKJUBU2_PUBLISHED_AFTER.isoformat()}"
        )
        source_videos = await self._video_fetch_port.fetch_channel_videos(
            channel_ids=DDAKJUBU2_CHANNEL_IDS,
            published_after=DDAKJUBU2_PUBLISHED_AFTER,
        )
        print(f"[ddakjubu2] 채널에서 조회된 영상 수: {len(source_videos)}")

        if not source_videos:
            print("[ddakjubu2] 학습 대상 영상이 존재하지 않습니다.")
            return LearnDdakjubu2Response(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=0,
                videos=[],
            )

        sorted_videos = self._sort_and_deduplicate(source_videos)
        print(f"[ddakjubu2] 중복 제거 및 정렬 후 영상 수: {len(sorted_videos)}")

        existing_video_ids = self._note_writer_port.load_existing_video_ids()
        print(f"[ddakjubu2] 기존 파일에 기록된 video_id 수: {len(existing_video_ids)}")

        new_videos = [v for v in sorted_videos if v.video_id not in existing_video_ids]
        skipped = len(sorted_videos) - len(new_videos)
        print(f"[ddakjubu2] 신규 학습 대상: {len(new_videos)}, 중복 skip: {skipped}")

        if not new_videos:
            print("[ddakjubu2] 새로 학습할 영상이 없습니다.")
            return LearnDdakjubu2Response(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=skipped,
                videos=[],
            )

        batch_buffer: List[LearningNote] = []
        all_notes: List[LearningNote] = []
        file_path = ""
        for idx, video in enumerate(new_videos, start=1):
            print(
                f"[ddakjubu2] ({idx}/{len(new_videos)}) 학습 시작 "
                f"video_id={video.video_id} title={video.title[:40]}",
                flush=True,
            )
            try:
                video.summary = await self._video_summarization_port.summarize(video)
                note = await self._video_learning_port.learn(video)
                print(
                    f"[ddakjubu2]   - 요약 {len(video.summary)}자, "
                    f"종목 {len(note.stock_insights)}개",
                    flush=True,
                )
                batch_buffer.append(note)
                all_notes.append(note)
            except Exception as e:
                print(
                    f"[ddakjubu2]   ! 학습 실패 video_id={video.video_id} error={e}",
                    flush=True,
                )
                continue

            if len(batch_buffer) >= BATCH_SAVE_SIZE:
                file_path = self._note_writer_port.append_notes(batch_buffer)
                print(
                    f"[ddakjubu2] 배치 저장 완료 batch={len(batch_buffer)} "
                    f"cumulative={len(all_notes)}/{len(new_videos)} path={file_path}",
                    flush=True,
                )
                batch_buffer = []

        if batch_buffer:
            file_path = self._note_writer_port.append_notes(batch_buffer)
            print(
                f"[ddakjubu2] 마지막 배치 저장 완료 batch={len(batch_buffer)} "
                f"cumulative={len(all_notes)}/{len(new_videos)} path={file_path}",
                flush=True,
            )

        if not all_notes:
            print("[ddakjubu2] 학습 결과가 존재하지 않습니다.")
            return LearnDdakjubu2Response(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=skipped,
                videos=[],
            )

        print(
            f"[ddakjubu2] 파이프라인 종료: file_path={file_path}, "
            f"processed={len(all_notes)}, skipped_duplicates={skipped}",
            flush=True,
        )

        items = [
            LearnedVideoItem(
                video_id=note.video_id,
                video_title=note.video_title,
                program_category=note.program_category,
                stock_count=len(note.stock_insights),
            )
            for note in all_notes
        ]

        return LearnDdakjubu2Response(
            file_path=file_path,
            processed_count=len(all_notes),
            skipped_duplicate_count=skipped,
            videos=items,
        )

    @staticmethod
    def _sort_and_deduplicate(videos: List[SourceVideo]) -> List[SourceVideo]:
        unique: dict[str, SourceVideo] = {}
        for video in videos:
            if video.video_id and video.video_id not in unique:
                unique[video.video_id] = video
        return sorted(
            unique.values(),
            key=lambda v: v.published_at,
            reverse=True,
        )

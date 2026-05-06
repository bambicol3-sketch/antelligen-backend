import json
import logging
from datetime import datetime

from app.domains.macro.adapter.outbound.cache.market_risk_snapshot_store import (
    get_market_risk_snapshot_store,
)
from app.domains.macro.adapter.outbound.external.langchain_risk_judgement_adapter import (
    LangChainRiskJudgementAdapter,
)
from app.domains.macro.adapter.outbound.external.youtube_macro_video_client import (
    YoutubeMacroVideoClient,
)
from app.domains.macro.adapter.outbound.file.study_note_file_reader import StudyNoteFileReader
from app.domains.macro.application.usecase.judge_market_risk_usecase import (
    JudgeMarketRiskUseCase,
)
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.config.settings import get_settings
from app.infrastructure.external.openai_responses_client import get_openai_responses_client

logger = logging.getLogger(__name__)

# Redis 영속 캐시 — 프로세스 재시작 후에도 직전 스냅샷을 메모리 store 로 복원하여
# YouTube/LLM 재호출(quota 소모)을 회피한다. TTL 은 일일 5시 스케줄 + 여유 버퍼.
MACRO_SNAPSHOT_REDIS_KEY = "macro:market_risk_snapshot"
MACRO_SNAPSHOT_REDIS_TTL_SECONDS = 25 * 3600


async def job_refresh_market_risk() -> None:
    """거시 경제 리스크 판단 스냅샷을 새로 계산해 메모리 + Redis 캐시에 저장."""
    print("[macro.job] 거시 경제 리스크 판단 스냅샷 갱신 시작")
    settings = get_settings()
    try:
        note_reader = StudyNoteFileReader()
        video_client = YoutubeMacroVideoClient(api_key=settings.youtube_api_key)
        llm_adapter = LangChainRiskJudgementAdapter(client=get_openai_responses_client())

        response = await JudgeMarketRiskUseCase(
            note_port=note_reader,
            video_port=video_client,
            llm_port=llm_adapter,
        ).execute()

        store = get_market_risk_snapshot_store()

        # LLM 타임아웃/파싱 실패 등으로 UNKNOWN 이 떨어진 경우 직전 정상 스냅샷을
        # 덮어쓰지 않는다. 직전 스냅샷이 없으면(콜드 스타트) 어쩔 수 없이 UNKNOWN 저장.
        if response.status == "UNKNOWN":
            existing = store.get()
            if existing is not None:
                print(
                    f"[macro.job] ⚠ LLM 결과 UNKNOWN — 기존 스냅샷 유지 "
                    f"(prev_status={existing.response.status}, "
                    f"prev_updated_at={existing.updated_at.isoformat()})"
                )
                return
            print("[macro.job] ⚠ LLM 결과 UNKNOWN + 직전 스냅샷 없음 — 콜드 스타트로 UNKNOWN 저장")

        updated_at = datetime.now()
        store.set(response, updated_at=updated_at)
        await _persist_snapshot_to_redis(response, updated_at)
        print(
            f"[macro.job] ✅ 스냅샷 갱신 완료 status={response.status} "
            f"reasons={len(response.reasons)}"
        )
    except Exception as exc:
        print(f"[macro.job] ❌ 스냅샷 갱신 실패: {exc}")
        logger.exception("[macro.job] 스냅샷 갱신 실패: %s", exc)


async def _persist_snapshot_to_redis(response, updated_at: datetime) -> None:
    try:
        payload = json.dumps(
            {
                "response": response.model_dump(mode="json"),
                "updated_at": updated_at.isoformat(),
            },
            ensure_ascii=False,
        )
        await redis_client.setex(
            MACRO_SNAPSHOT_REDIS_KEY,
            MACRO_SNAPSHOT_REDIS_TTL_SECONDS,
            payload,
        )
    except Exception as e:
        logger.warning("[macro.job] Redis 스냅샷 저장 실패: %s", e)

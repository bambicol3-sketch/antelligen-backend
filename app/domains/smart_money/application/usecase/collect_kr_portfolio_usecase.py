import asyncio
import logging
from datetime import date, datetime

from app.domains.smart_money.adapter.outbound.external.dart_client import DartClient
from app.domains.smart_money.application.port.out.kr_portfolio_repository_port import KrPortfolioRepositoryPort
from app.domains.smart_money.domain.entity.kr_portfolio import KrPortfolioHolding

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────
# 수집 대상 국내 유명 투자자 목록
# key: DART 보고인명(flr_nm) 에 포함될 문자열
# value: 투자자 유형
# ──────────────────────────────────────────────────────────
KR_INVESTOR_MAP: dict[str, str] = {
    "국민연금공단": "PENSION",
    "미래에셋자산운용": "ASSET_MANAGER",
    "삼성자산운용": "ASSET_MANAGER",
    "KB자산운용": "ASSET_MANAGER",
    "신한자산운용": "ASSET_MANAGER",
    "한국투자신탁운용": "ASSET_MANAGER",
    "NH-아문디자산운용": "ASSET_MANAGER",
    "박현주": "INDIVIDUAL",
    "강방천": "INDIVIDUAL",
    "이채원": "INDIVIDUAL",
}

_TOP_N = 800        # DART corp_code XML 상장주 (오름차순 = 오래된 대형주 우선)
_CONCURRENCY = 10   # 동시 DART API 요청 수


def _find_investor(flr_nm: str) -> str | None:
    """flr_nm(보고인명)이 KR_INVESTOR_MAP의 키와 부분 일치하는지 확인한다."""
    for name in KR_INVESTOR_MAP:
        if name in flr_nm or flr_nm in name:
            return name
    return None


def _parse_int(raw: str) -> int:
    cleaned = raw.replace(",", "").strip()
    return int(cleaned) if cleaned.lstrip("-").isdigit() else 0


def _parse_float(raw: str) -> float:
    cleaned = raw.replace("%", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_date(raw: str) -> date:
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return date.today()


class CollectKrPortfolioUseCase:

    def __init__(self, dart_client: DartClient, repository: KrPortfolioRepositoryPort):
        self._dart = dart_client
        self._repository = repository

    async def execute(self) -> dict:
        # 1) DART corp_code 맵 다운로드 (1회)
        logger.info("[kr_portfolio] DART corp_code 맵 다운로드")
        await self._dart.ensure_stock_info_map()

        # 2) 종목 코드 목록 추출
        stock_codes = self._dart.get_stock_codes_sorted(_TOP_N)
        if not stock_codes:
            return {"total_saved": 0, "error": "DART corp_code 맵 없음"}

        logger.info("[kr_portfolio] 수집 대상 종목 수: %d (동시 요청: %d)", len(stock_codes), _CONCURRENCY)

        # 3) Phase 1 — DART API 병렬 조회 (HTTP I/O만 수행)
        semaphore = asyncio.Semaphore(_CONCURRENCY)
        matched_records: list[tuple[dict, str, str]] = []  # (sh, stock_code, stock_name)

        async def fetch_stock(stock_code: str) -> list[tuple[dict, str, str]]:
            corp_info = self._dart.get_corp_info(stock_code)
            if not corp_info:
                return []
            async with semaphore:
                shareholders = await self._dart.get_major_shareholders(corp_info["corp_code"])
            results = []
            for sh in shareholders:
                repror = sh.get("repror", "")
                if _find_investor(repror):
                    results.append((sh, stock_code, corp_info["corp_name"]))
            return results

        batches = await asyncio.gather(*[fetch_stock(code) for code in stock_codes])
        for batch in batches:
            matched_records.extend(batch)

        logger.info("[kr_portfolio] DART 조회 완료, 매칭 레코드: %d건", len(matched_records))

        # 4) Phase 2 — DB 순차 저장
        total_saved = 0
        for sh, stock_code, stock_name in matched_records:
            if await self._process_shareholder(sh, stock_code, stock_name):
                total_saved += 1

        logger.info("[kr_portfolio] 수집 완료: %d건 저장", total_saved)
        return {"total_saved": total_saved}

    async def _process_shareholder(self, sh: dict, stock_code: str, stock_name: str) -> bool:
        """단일 대량보유 레코드를 처리하여 DB에 저장한다. 저장 성공 시 True 반환."""
        repror = sh.get("repror", "")
        matched = _find_investor(repror)
        if not matched:
            return False

        logger.info("[kr_portfolio] 매칭 repror=%s stkqy=%s stkrt=%s", repror, sh.get("stkqy"), sh.get("stkrt"))
        shares_held = _parse_int(sh.get("stkqy", "0"))
        ownership_ratio = _parse_float(sh.get("stkrt", "0"))
        reported_at = _parse_date(sh.get("rcept_dt", ""))

        # 기존 레코드와 비교하여 change_type 결정 (shares_held=0은 미수집으로 취급)
        existing = await self._repository.find_one(matched, stock_code)
        if existing is None or existing.shares_held == 0:
            change_type = "NEW"
        elif shares_held > existing.shares_held:
            change_type = "INCREASED"
        elif shares_held < existing.shares_held:
            change_type = "DECREASED"
        else:
            change_type = existing.change_type

        await self._repository.upsert(KrPortfolioHolding(
            investor_name=matched,
            investor_type=KR_INVESTOR_MAP[matched],
            stock_code=stock_code,
            stock_name=stock_name,
            shares_held=shares_held,
            ownership_ratio=ownership_ratio,
            change_type=change_type,
            reported_at=reported_at,
        ))
        return True

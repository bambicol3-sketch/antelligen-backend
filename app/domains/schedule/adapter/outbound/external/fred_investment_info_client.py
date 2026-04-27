"""FRED(Federal Reserve Economic Data) 기반 투자 정보 조회 어댑터.

FRED API 문서: https://fred.stlouisfed.org/docs/api/fred/
- observations endpoint 로 최신 관측치 1건 획득
- 결측치(".")는 건너뛰고 직전 유효값을 사용
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx

from app.domains.schedule.application.port.out.investment_info_provider_port import (
    InvestmentInfoProviderPort,
)
from app.domains.schedule.domain.entity.investment_info import InvestmentInfo
from app.domains.schedule.domain.value_object.investment_info_type import InvestmentInfoType

logger = logging.getLogger(__name__)

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# InvestmentInfoType -> (FRED series_id, unit, description)
_SERIES_TABLE: dict[InvestmentInfoType, Tuple[str, str, str]] = {
    # 미국 국채 금리
    InvestmentInfoType.INTEREST_RATE: (
        "DGS10",
        "%",
        "미국 10년물 국채 금리 (10-Year Treasury Constant Maturity Rate, Daily, FRED)",
    ),
    InvestmentInfoType.US_T2Y: (
        "DGS2",
        "%",
        "미국 2년물 국채 금리 (2-Year Treasury Constant Maturity Rate, Daily, FRED)",
    ),
    InvestmentInfoType.US_T10Y: (
        "DGS10",
        "%",
        "미국 10년물 국채 금리 (10-Year Treasury Constant Maturity Rate, Daily, FRED)",
    ),
    InvestmentInfoType.US_T20Y: (
        "DGS20",
        "%",
        "미국 20년물 국채 금리 (20-Year Treasury Constant Maturity Rate, Daily, FRED)",
    ),
    # 원자재
    # OIL_PRICE(WTI) 는 FRED 의 DCOILWTICO(Cushing 물리 현물가) 가 수일~1주 발표 지연이 있고
    # 최근 병목 구간엔 NYMEX 선물 대비 10 달러 이상 벌어져 "WTI" 통상 가격과 괴리가 큼.
    # 시장에서 흔히 "WTI"라고 부르는 실시간 NYMEX 근월물 선물(`CL=F`) 을 Yahoo 로 폴백.
    # GOLD 는 FRED 공식 일간 시리즈 접근이 제한적이어서 Yahoo(`GC=F`) 로 폴백
    # 환율
    InvestmentInfoType.EXCHANGE_RATE: (
        "DEXKOUS",
        "KRW/USD",
        "원/달러 환율 (South Korean Won / U.S. Dollar, Daily, FRED)",
    ),
    InvestmentInfoType.USD_JPY: (
        "DEXJPUS",
        "JPY/USD",
        "달러/엔 환율 (Japanese Yen / U.S. Dollar, Daily, FRED)",
    ),
    # 달러 인덱스 (DXY) 는 FRED 에 ICE DXY 공식 시리즈가 없음 (DTWEXM 은 2020년 discontinued,
    # DTWEXBGS 는 Fed Broad Dollar Index 로 바스켓/기준연도가 다른 별개 지표).
    # Yahoo Finance (`DX-Y.NYB`) 로 폴백.
    # 주요 지수
    InvestmentInfoType.VIX: (
        "VIXCLS",
        "index",
        "CBOE 변동성 지수 (VIX, Daily Close, FRED)",
    ),
    InvestmentInfoType.SP_500: (
        "SP500",
        "index",
        "S&P 500 지수 (S&P 500, Daily, FRED)",
    ),
    InvestmentInfoType.NASDAQ_100: (
        "NASDAQ100",
        "index",
        "나스닥 100 지수 (NASDAQ 100 Index, Daily, FRED)",
    ),
    # DRAM 현물 가격 — DRAMeXchange 는 유료. FRED 반도체 PPI 를 대리 지표로 사용.
    InvestmentInfoType.DRAM_EXCHANGE: (
        "PCU334413334413",
        "index (Dec 1998=100)",
        "반도체 산업 PPI — DRAMeXchange 대리 지표 "
        "(Producer Price Index by Industry: Semiconductor and Related Device "
        "Manufacturing, Monthly, FRED)",
    ),
    # KOSPI_200, GOLD, BALTIC_DRY_INDEX 는 FRED 에 없음 — Yahoo 로 폴백
}


class FredInvestmentInfoClient(InvestmentInfoProviderPort):
    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 5.0,
        lookback: int = 30,
        max_retries: int = 2,
        initial_backoff: float = 1.0,
    ):
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._lookback = lookback  # 결측/휴일 고려하여 최근 N 관측치에서 유효값을 찾는다
        # FRED 가 한국 IP/외국망에서 가끔 5xx 를 토하는 패턴 — 짧은 backoff retry 로 회복.
        # 4xx (인증/파라미터 결함) 는 deterministic 이므로 retry 하지 않는다.
        self._max_retries = max_retries
        self._initial_backoff = initial_backoff

    def supports(self, info_type: InvestmentInfoType) -> bool:
        return info_type in _SERIES_TABLE

    async def fetch(self, info_type: InvestmentInfoType) -> InvestmentInfo:
        if info_type not in _SERIES_TABLE:
            raise ValueError(f"FRED 가 지원하지 않는 유형입니다: {info_type}")
        if not self._api_key:
            raise RuntimeError("FRED_API_KEY 가 설정되지 않았습니다.")

        series_id, unit, base_description = _SERIES_TABLE[info_type]
        print(
            f"[schedule.fred] 요청 type={info_type.value} series_id={series_id}"
        )

        params = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": str(self._lookback),
        }

        response = await self._fetch_with_retry(params)

        if response.status_code != 200:
            raise RuntimeError(
                f"FRED 응답 오류 status={response.status_code} "
                f"body={response.text[:200]}"
            )

        data = response.json()
        observations = data.get("observations") or []
        if not observations:
            raise RuntimeError(f"FRED 관측치 없음 series_id={series_id}")

        latest_value, latest_date = self._pick_latest_valid(observations)
        if latest_value is None:
            raise RuntimeError(
                f"FRED 유효 관측치를 찾지 못했습니다 series_id={series_id} "
                f"(최근 {len(observations)}건 모두 결측)"
            )

        retrieved_at = datetime.now(timezone.utc)
        description = f"{base_description} · 관측일: {latest_date}"

        print(
            f"[schedule.fred] 응답 series_id={series_id} value={latest_value} "
            f"observation_date={latest_date}"
        )

        return InvestmentInfo(
            info_type=info_type,
            symbol=series_id,
            value=latest_value,
            unit=unit,
            retrieved_at=retrieved_at,
            source="FRED (Federal Reserve Economic Data)",
            description=description,
        )

    async def _fetch_with_retry(self, params: dict) -> httpx.Response:
        """5xx 와 일시 네트워크 오류에 대해 짧은 backoff retry. 4xx 는 즉시 반환.

        반환된 response 의 status_code 가 5xx 면 호출자가 예외 처리.
        모든 retry 가 5xx 면 마지막 5xx response 를 반환.
        """
        backoff = self._initial_backoff
        last_response: Optional[httpx.Response] = None

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(FRED_BASE_URL, params=params)
            except httpx.RequestError as exc:
                if attempt < self._max_retries:
                    logger.info(
                        "[schedule.fred] 네트워크 오류 재시도 attempt=%d/%d "
                        "err=%r backoff=%.1fs",
                        attempt + 1, self._max_retries, exc, backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise

            if 500 <= response.status_code < 600:
                last_response = response
                if attempt < self._max_retries:
                    logger.info(
                        "[schedule.fred] 5xx 재시도 attempt=%d/%d "
                        "status=%d backoff=%.1fs",
                        attempt + 1, self._max_retries,
                        response.status_code, backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                return response

            return response

        # unreachable in practice — 모든 5xx 는 위 return 에서 처리
        assert last_response is not None
        return last_response

    @staticmethod
    def _pick_latest_valid(observations: list) -> Tuple[Optional[float], Optional[str]]:
        """결측치(".")를 건너뛰고 최신 유효 관측치를 반환한다. sort_order=desc 전제."""
        for obs in observations:
            raw = obs.get("value")
            date = obs.get("date")
            if raw in (None, ".", ""):
                continue
            try:
                return float(raw), date
            except (TypeError, ValueError):
                continue
        return None, None

import io
import logging
import zipfile
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

_DART_BASE = "https://opendart.fss.or.kr/api"


class DartClient:
    """DART OpenAPI 클라이언트.

    주요 기능:
    - DART 전체 기업 corp_code XML 다운로드 → {stock_code: {corp_code, corp_name}} 맵 구성
    - majorstock.json 조회: 특정 회사의 5% 이상 대량보유 현황
    """

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._stock_info: dict[str, dict] | None = None  # stock_code → {corp_code, corp_name}
        self._client: httpx.AsyncClient | None = None

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    async def _get_json(self, path: str, params: dict) -> dict:
        params = {"crtfc_key": self._api_key, **params}
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        resp = await self._client.get(f"{_DART_BASE}/{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def _get_bytes(self, path: str, params: dict) -> bytes:
        params = {"crtfc_key": self._api_key, **params}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(f"{_DART_BASE}/{path}", params=params)
            resp.raise_for_status()
            return resp.content

    # ──────────────────────────────────────────────
    # Corp code map
    # ──────────────────────────────────────────────

    async def _build_stock_info_map(self) -> dict[str, dict]:
        """DART corpCode.xml ZIP을 다운로드하여 stock_code → {corp_code, corp_name} 맵을 구성한다."""
        try:
            content = await self._get_bytes("corpCode.xml", {})
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                xml_name = next((n for n in z.namelist() if n.lower().endswith(".xml")), None)
                if not xml_name:
                    logger.error("[dart] corp_code ZIP에 XML 파일이 없습니다.")
                    return {}
                xml_bytes = z.read(xml_name)

            root = ET.fromstring(xml_bytes)
            mapping: dict[str, dict] = {}
            for item in root.findall(".//list"):
                corp_code = (item.findtext("corp_code") or "").strip()
                corp_name = (item.findtext("corp_name") or "").strip()
                stock_code = (item.findtext("stock_code") or "").strip()
                if corp_code and stock_code and len(stock_code) == 6:
                    mapping[stock_code] = {"corp_code": corp_code, "corp_name": corp_name}

            logger.info("[dart] stock_info 맵 구성 완료: %d건", len(mapping))
            return mapping
        except Exception as e:
            logger.error("[dart] stock_info 맵 구성 실패: %s", e)
            return {}

    async def ensure_stock_info_map(self) -> None:
        """corp_code 맵이 아직 로드되지 않았으면 다운로드한다."""
        if self._stock_info is None:
            self._stock_info = await self._build_stock_info_map()

    def get_corp_info(self, stock_code: str) -> dict | None:
        """stock_code에 해당하는 corp_code와 corp_name을 반환한다."""
        if self._stock_info is None:
            return None
        return self._stock_info.get(stock_code)

    def get_stock_codes_sorted(self, limit: int = 500) -> list[str]:
        """corp_code 맵에서 상장 종목 코드를 오름차순으로 반환한다 (pykrx 불필요).

        stock_code 오름차순 = 역사적으로 오래된 기업 순 → 대형 우량주 위주로 포함됨.
        """
        if not self._stock_info:
            return []
        return sorted(self._stock_info.keys())[:limit]

    # ──────────────────────────────────────────────
    # DART API
    # ──────────────────────────────────────────────

    async def get_major_shareholders(self, corp_code: str) -> list[dict]:
        """특정 회사의 5% 이상 대량보유 현황을 조회한다 (majorstock.json).

        응답 주요 필드:
          repror      : 보고인명 (투자자/기관명)
          rcept_dt    : 접수일자 (YYYY-MM-DD)
          stkqy       : 보유주식수 (쉼표 포함 문자열, 예: "1,199,540,016")
          stkrt       : 보유비율 (%, 예: "20.09")
          corp_name   : 발행회사명
          stock_code  : 종목코드
        """
        try:
            resp = await self._get_json("majorstock.json", {"corp_code": corp_code})
            if resp.get("status") != "000":
                return []
            return resp.get("list", [])
        except Exception as e:
            logger.debug("[dart] majorstock 조회 실패 corp_code=%s: %s", corp_code, e)
            return []

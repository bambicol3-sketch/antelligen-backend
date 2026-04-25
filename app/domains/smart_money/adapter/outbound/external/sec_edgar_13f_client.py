import logging
import re
from datetime import date
from xml.etree import ElementTree as ET

import httpx

from app.domains.smart_money.adapter.outbound.external.openfigi_ticker_resolver import resolve_tickers_batch
from app.domains.smart_money.application.port.out.global_portfolio_fetch_port import GlobalPortfolioFetchPort
from app.domains.smart_money.domain.entity.global_portfolio import ChangeType, GlobalPortfolio

logger = logging.getLogger(__name__)

_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
_FILING_DIR_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/"
_NS = {"ns": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}

# 13F infotable XML 파일명 패턴
_INFOTABLE_PATTERN = re.compile(r'href="([^"]*(?:infotable|information_table|\d+)\.xml)"', re.IGNORECASE)


def _parse_period(primary_doc_xml: str) -> date | None:
    """primary_doc.xml에서 period of report를 파싱한다."""
    match = re.search(r"<periodofreport>([^<]+)</periodofreport>", primary_doc_xml, re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1).strip()  # 예: 12-31-2024 or 2024-12-31
    for fmt in ("%m-%d-%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_infotable(xml_text: str) -> list[dict]:
    """13F informationTable XML을 파싱하여 보유 종목 리스트를 반환한다."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning("[sec_edgar] XML 파싱 실패: %s", e)
        return []

    holdings: list[dict] = []
    # namespace 있는 경우와 없는 경우 모두 처리
    for tag in ("ns:infoTable", "infoTable"):
        ns = _NS if tag.startswith("ns:") else {}
        entries = root.findall(tag, ns)
        if entries:
            for entry in entries:
                def _text(t: str) -> str:
                    el = entry.find(t, ns) if ns else entry.find(t)
                    return el.text.strip() if el is not None and el.text else ""
                def _text_ns(t1, t2):
                    return _text(t1) or _text(t2)

                name = _text_ns("ns:nameOfIssuer", "nameOfIssuer")
                cusip = _text_ns("ns:cusip", "cusip")
                value_str = _text_ns("ns:value", "value")
                shrs_el = entry.find("ns:shrsOrPrnAmt/ns:sshPrnamt", ns)
                if shrs_el is None:
                    shrs_el = entry.find("shrsOrPrnAmt/sshPrnamt")
                shares_str = shrs_el.text.strip() if shrs_el is not None and shrs_el.text else "0"

                if not cusip or not name:
                    continue

                holdings.append({
                    "name": name,
                    "cusip": cusip,
                    "value": int(value_str.replace(",", "")) if value_str else 0,
                    "shares": int(shares_str.replace(",", "")) if shares_str else 0,
                })
            break

    return holdings


def _aggregate_by_cusip(raw: list[dict]) -> list[dict]:
    """동일 CUSIP 중복 항목(투자재량 구분 등)을 집계한다."""
    agg: dict[str, dict] = {}
    for item in raw:
        cusip = item["cusip"]
        if cusip in agg:
            agg[cusip]["shares"] += item["shares"]
            agg[cusip]["value"] += item["value"]
        else:
            agg[cusip] = dict(item)
    return list(agg.values())


class SecEdgar13FClient(GlobalPortfolioFetchPort):

    def __init__(self, user_agent: str):
        self._headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}

    async def fetch_latest(self, investor_name: str, cik: str) -> list[GlobalPortfolio]:
        cik_padded = cik.zfill(10)
        cik_int = int(cik)

        # 1. 최신 13F-HR 공시 조회
        acc, filing_date = await self._get_latest_13f_accession(cik_padded)
        if not acc:
            logger.warning("[sec_edgar] %s — 13F 공시 없음", investor_name)
            return []

        acc_nodash = acc.replace("-", "")

        # 2. 공시 디렉토리에서 파일 목록 조회
        dir_url = _FILING_DIR_URL.format(cik_int=cik_int, acc_nodash=acc_nodash)
        infotable_url, primary_doc_url = await self._find_xml_files(dir_url, acc_nodash, cik_int)

        # 3. period of report 파싱
        reported_at = await self._fetch_period(primary_doc_url)
        if not reported_at:
            reported_at = filing_date  # 폴백: 공시 날짜 사용

        # 4. infotable XML 파싱
        if not infotable_url:
            logger.warning("[sec_edgar] %s — infotable XML 파일을 찾을 수 없음", investor_name)
            return []

        raw_holdings = await self._fetch_infotable(infotable_url)
        if not raw_holdings:
            return []

        aggregated = _aggregate_by_cusip(raw_holdings)

        # 5. CUSIP → 티커 일괄 조회 (OpenFIGI)
        cusips = [h["cusip"] for h in aggregated]
        ticker_map = await resolve_tickers_batch(cusips)

        # 6. GlobalPortfolio 엔티티 생성 (change_type은 UseCase에서 덮어씀)
        portfolios = [
            GlobalPortfolio(
                investor_name=investor_name,
                ticker=ticker_map.get(h["cusip"]),
                stock_name=h["name"],
                cusip=h["cusip"],
                shares=h["shares"],
                market_value=h["value"],
                portfolio_weight=0.0,
                reported_at=reported_at,
                change_type=ChangeType.NEW,  # placeholder
            )
            for h in aggregated
        ]

        logger.info("[sec_edgar] %s %s — %d개 종목 파싱 완료", investor_name, reported_at, len(portfolios))
        return portfolios

    async def _get_latest_13f_accession(self, cik_padded: str) -> tuple[str | None, date | None]:
        url = _SUBMISSIONS_URL.format(cik=cik_padded)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=self._headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.error("[sec_edgar] submissions 조회 실패 CIK=%s: %s", cik_padded, exc)
            return None, None

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accs = filings.get("accessionNumber", [])
        dates = filings.get("filingDate", [])

        for form, acc, d in zip(forms, accs, dates):
            if form == "13F-HR":
                from datetime import datetime
                filing_date = datetime.strptime(d, "%Y-%m-%d").date()
                return acc, filing_date

        return None, None

    async def _find_xml_files(
        self, dir_url: str, acc_nodash: str, cik_int: int
    ) -> tuple[str | None, str | None]:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(dir_url, headers=self._headers)
                resp.raise_for_status()
                html = resp.text
        except Exception as exc:
            logger.warning("[sec_edgar] 디렉토리 조회 실패 %s: %s", dir_url, exc)
            return None, None

        xml_hrefs = re.findall(r'href="(/Archives/edgar/data/[^"]+\.xml)"', html, re.IGNORECASE)

        infotable_url: str | None = None
        primary_url: str | None = None

        for href in xml_hrefs:
            full_url = f"https://www.sec.gov{href}"
            name = href.lower()
            if "primary" in name or "primary_doc" in name:
                primary_url = full_url
            elif infotable_url is None:  # 첫 번째 숫자형 XML이 보통 infotable
                infotable_url = full_url

        # primary_doc이 따로 없으면 xslForm13F 경로로 시도
        if not primary_url:
            primary_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/primary_doc.xml"

        return infotable_url, primary_url

    async def _fetch_period(self, primary_doc_url: str | None) -> date | None:
        if not primary_doc_url:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(primary_doc_url, headers=self._headers)
                if resp.status_code != 200:
                    return None
                return _parse_period(resp.text)
        except Exception:
            return None

    async def _fetch_infotable(self, url: str) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=self._headers)
                resp.raise_for_status()
                return _parse_infotable(resp.text)
        except Exception as exc:
            logger.error("[sec_edgar] infotable fetch 실패 %s: %s", url, exc)
            return []

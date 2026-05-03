"""나딱구 공부방 산업군 분석 페이지 크롤러.

흐름은 mse_market_analysis 의 크롤러와 동일하다.
인증 게이트가 패스키 전용일 수 있으므로 cookies 옵션도 지원한다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.domains.mse_sectors.adapter.outbound.external.mse_sectors_html_parser import (
    parse_sectors_html,
)
from app.domains.mse_sectors.application.port.sectors_crawl_port import SectorsCrawlPort
from app.domains.mse_sectors.domain.entity.sectors_snapshot import SectorsSnapshot
from app.domains.mse_sectors.domain.value_object.crawl_status import CrawlStatus

logger = logging.getLogger(__name__)


_LOGIN_FORM_HINTS = ("로그인", "login", "비밀번호", "password")
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko,en-US;q=0.8,en;q=0.6",
}


class SectorsCrawler(SectorsCrawlPort):
    def __init__(
        self,
        page_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        login_url: Optional[str] = None,
        cookies: Optional[dict[str, str]] = None,
        timeout_seconds: float = 15.0,
    ):
        self._page_url = page_url
        self._username = username or ""
        self._password = password or ""
        self._login_url = login_url
        self._cookies = cookies or {}
        self._timeout_seconds = timeout_seconds
        self.last_fetched_html: Optional[str] = None

    async def crawl(self) -> SectorsSnapshot:
        now = datetime.now(timezone.utc)
        self.last_fetched_html = None
        try:
            html = await self._fetch_html()
        except httpx.HTTPError as e:
            logger.exception("mse_sectors fetch failed: %s", e)
            return SectorsSnapshot(
                id=None,
                source_url=self._page_url,
                collected_at=now,
                status=CrawlStatus.FAILED,
                error_reason=f"HTTP error: {e!s}",
            )

        if html is None:
            return SectorsSnapshot(
                id=None,
                source_url=self._page_url,
                collected_at=now,
                status=CrawlStatus.FAILED,
                error_reason="authentication failed or empty response",
            )

        self.last_fetched_html = html
        metrics, industries, sections = parse_sectors_html(
            html, base_url=self._page_url
        )
        if not metrics and not industries and not sections:
            return SectorsSnapshot(
                id=None,
                source_url=self._page_url,
                collected_at=now,
                status=CrawlStatus.STRUCTURE_CHANGED,
                error_reason="no recognizable sections in response HTML",
            )

        return SectorsSnapshot(
            id=None,
            source_url=self._page_url,
            collected_at=now,
            status=CrawlStatus.SUCCESS,
            stock_metrics=metrics,
            leading_industries=industries,
            sections=sections,
        )

    async def _fetch_html(self) -> Optional[str]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self._timeout_seconds,
            headers=_DEFAULT_HEADERS,
            cookies=self._cookies or None,
        ) as client:
            response = await client.get(self._page_url)
            response.raise_for_status()

            if not self._looks_like_login(response.text):
                return response.text

            if self._cookies and not (self._username and self._password):
                logger.warning(
                    "mse_sectors cookies were provided but server returned a login page"
                    " — cookie may have expired"
                )
                return None

            if not (self._username and self._password):
                logger.warning(
                    "mse_sectors page requires login but credentials are not configured"
                )
                return None

            login_endpoint, payload = self._build_login_payload(response)
            login_response = await client.post(login_endpoint, data=payload)
            login_response.raise_for_status()

            if self._looks_like_login(login_response.text):
                logger.warning("mse_sectors login appears to have failed")
                return None

            final = await client.get(self._page_url)
            final.raise_for_status()
            if self._looks_like_login(final.text):
                return None
            return final.text

    @staticmethod
    def _looks_like_login(html: str) -> bool:
        if not html:
            return False
        soup = BeautifulSoup(html, "html.parser")
        if soup.find("input", {"type": "password"}):
            return True
        title = soup.find("title")
        title_text = (title.get_text(strip=True) if title else "").lower()
        if any(hint in title_text for hint in _LOGIN_FORM_HINTS) or "passkey" in title_text or "패스키" in title_text:
            return True
        text = soup.get_text(" ", strip=True).lower()
        hits = sum(1 for hint in _LOGIN_FORM_HINTS if hint in text)
        if "패스키" in text or "passkey" in text:
            hits += 1
        return hits >= 2 and not soup.find("table")

    def _build_login_payload(
        self, login_page: httpx.Response
    ) -> tuple[str, dict[str, str]]:
        soup = BeautifulSoup(login_page.text, "html.parser")
        form = soup.find("form")

        action = (form.get("action") if form else None) or self._login_url or str(login_page.url)
        login_endpoint = str(httpx.URL(str(login_page.url)).join(action))

        payload: dict[str, str] = {}
        if form:
            for hidden in form.find_all("input", {"type": "hidden"}):
                name = hidden.get("name")
                if name:
                    payload[name] = hidden.get("value", "")

        username_field = self._find_field_name(form, ("username", "userid", "user_id", "id", "email"))
        password_field = self._find_field_name(form, ("password", "passwd", "pw"))

        payload[username_field or "username"] = self._username
        payload[password_field or "password"] = self._password
        return login_endpoint, payload

    @staticmethod
    def _find_field_name(form, candidates: tuple[str, ...]) -> Optional[str]:
        if form is None:
            return None
        for name in candidates:
            if form.find("input", {"name": name}):
                return name
        for input_node in form.find_all("input"):
            name = (input_node.get("name") or "").lower()
            for candidate in candidates:
                if candidate in name:
                    return input_node.get("name")
        return None

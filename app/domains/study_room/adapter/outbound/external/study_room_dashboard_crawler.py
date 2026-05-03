"""나딱구 공부방 대시보드 크롤러.

페이지가 인증 게이트(로그인 폼) 뒤에 있으므로 다음 순서로 동작한다.

1) 대시보드 URL 에 GET → 응답이 로그인 폼이면 로그인 시도.
2) 로그인 폼 응답에서 hidden input(예: csrf_token) 을 추출해 함께 POST.
3) 인증 후 다시 대시보드 URL 을 GET 하여 HTML 본문을 받는다.
4) HTML 을 파서로 정규화하여 DashboardSnapshot 으로 반환한다.

자격 증명이 없거나 응답이 비정상이면 FAILED 상태의 스냅샷을 반환한다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.domains.study_room.application.port.dashboard_crawl_port import DashboardCrawlPort
from app.domains.study_room.adapter.outbound.external.study_room_html_parser import (
    parse_dashboard_html,
)
from app.domains.study_room.domain.entity.dashboard_snapshot import DashboardSnapshot
from app.domains.study_room.domain.value_object.crawl_status import CrawlStatus

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


class StudyRoomDashboardCrawler(DashboardCrawlPort):
    def __init__(
        self,
        dashboard_url: str,
        username: Optional[str],
        password: Optional[str],
        login_url: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ):
        self._dashboard_url = dashboard_url
        self._username = username or ""
        self._password = password or ""
        self._login_url = login_url
        self._timeout_seconds = timeout_seconds
        self.last_fetched_html: Optional[str] = None

    async def crawl(self) -> DashboardSnapshot:
        now = datetime.now(timezone.utc)
        self.last_fetched_html = None
        try:
            html = await self._fetch_dashboard_html()
        except httpx.HTTPError as e:
            logger.exception("study_room dashboard fetch failed: %s", e)
            return DashboardSnapshot(
                id=None,
                source_url=self._dashboard_url,
                collected_at=now,
                status=CrawlStatus.FAILED,
                error_reason=f"HTTP error: {e!s}",
            )

        if html is None:
            return DashboardSnapshot(
                id=None,
                source_url=self._dashboard_url,
                collected_at=now,
                status=CrawlStatus.FAILED,
                error_reason="authentication failed or empty response",
            )

        self.last_fetched_html = html
        metrics, industries, sections = parse_dashboard_html(
            html, base_url=self._dashboard_url
        )
        if not metrics and not industries and not sections:
            return DashboardSnapshot(
                id=None,
                source_url=self._dashboard_url,
                collected_at=now,
                status=CrawlStatus.STRUCTURE_CHANGED,
                error_reason="no recognizable dashboard sections in response HTML",
            )

        return DashboardSnapshot(
            id=None,
            source_url=self._dashboard_url,
            collected_at=now,
            status=CrawlStatus.SUCCESS,
            stock_metrics=metrics,
            leading_industries=industries,
            sections=sections,
        )

    async def _fetch_dashboard_html(self) -> Optional[str]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self._timeout_seconds,
            headers=_DEFAULT_HEADERS,
        ) as client:
            response = await client.get(self._dashboard_url)
            response.raise_for_status()

            if not self._looks_like_login(response.text):
                return response.text

            if not (self._username and self._password):
                logger.warning(
                    "study_room dashboard requires login but credentials are not configured"
                )
                return None

            login_endpoint, payload = self._build_login_payload(response)
            login_response = await client.post(login_endpoint, data=payload)
            login_response.raise_for_status()

            if self._looks_like_login(login_response.text):
                logger.warning("study_room dashboard login appears to have failed")
                return None

            final = await client.get(self._dashboard_url)
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
        text = soup.get_text(" ", strip=True).lower()
        hits = sum(1 for hint in _LOGIN_FORM_HINTS if hint in text)
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

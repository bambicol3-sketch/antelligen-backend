"""원본 산업군 분석 HTML 을 표준 도메인 모델로 정규화한다.

전략은 mse_market_analysis 의 파서와 동일하다.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag

from app.domains.mse_sectors.domain.entity.dashboard_section import DashboardSection
from app.domains.mse_sectors.domain.entity.leading_industry import LeadingIndustry
from app.domains.mse_sectors.domain.entity.stock_metric import StockMetric


_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")

_METRIC_HEADER_HINTS = {
    "wsma120": "wsma120",
    "slope120": "slope120",
    "curv120": "curv120",
    "z180": "z180",
    "escore": "escore",
    "align": "align",
    "momentum": "momentum",
    "현재가": "price",
    "가격": "price",
    "종가": "price",
    "등락률": "change_rate",
    "변동률": "change_rate",
    "수익률": "change_rate",
    "종목명": "name",
    "이름": "name",
    "종목코드": "code",
    "코드": "code",
    "티커": "code",
    "섹터": "sector",
    "sector": "sector",
    "업종": "industry",
    "industry": "industry",
}

_INDUSTRY_HEADER_HINTS = {
    "업종": "industry",
    "industry": "industry",
    "평균수익률": "avg_return",
    "평균 수익률": "avg_return",
    "수익률": "avg_return",
    "평균escore": "avg_escore",
    "평균 escore": "avg_escore",
    "escore": "avg_escore",
    "종목수": "member_count",
    "구성종목수": "member_count",
    "순위": "rank",
    "rank": "rank",
}


def _normalize_header(text: str) -> str:
    return re.sub(r"\s+", "", (text or "")).lower()


def _to_number(value: str) -> Optional[float]:
    if value is None:
        return None
    cleaned = value.replace(",", "").replace("%", "").strip()
    if cleaned in ("", "-", "—"):
        return None
    match = _NUMBER_RE.search(cleaned)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _to_int(value: str) -> Optional[int]:
    n = _to_number(value)
    return int(n) if n is not None else None


def _table_headers(table: Tag) -> list[str]:
    head = table.find("thead")
    if head:
        ths = head.find_all("th")
        if ths:
            return [th.get_text(strip=True) for th in ths]
    first_row = table.find("tr")
    if first_row:
        cells = first_row.find_all(["th", "td"])
        return [c.get_text(strip=True) for c in cells]
    return []


def _table_rows(table: Tag, header_count: int) -> Iterable[list[str]]:
    body = table.find("tbody") or table
    rows = body.find_all("tr")
    skip_first = body is table and table.find("thead") is None
    for idx, tr in enumerate(rows):
        if skip_first and idx == 0:
            continue
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        values = [c.get_text(" ", strip=True) for c in cells]
        if header_count and len(values) < header_count:
            values += [""] * (header_count - len(values))
        yield values


def _classify_table(headers: list[str]) -> str:
    norm = {_normalize_header(h) for h in headers}
    if any(h in norm for h in ("wsma120", "slope120", "z180", "escore")) and any(
        h in norm for h in ("종목명", "이름", "종목코드", "코드", "티커")
    ):
        return "stock_metric"
    if "업종" in norm or "industry" in norm:
        if any(h in norm for h in ("평균수익률", "수익률", "escore", "평균escore")):
            return "leading_industry"
    return "generic"


def _map_metric_row(headers: list[str], values: list[str]) -> Optional[StockMetric]:
    fields: dict[str, Any] = {}
    for header, raw in zip(headers, values):
        key = _METRIC_HEADER_HINTS.get(_normalize_header(header))
        if key is None:
            continue
        if key in ("name", "code", "sector", "industry"):
            fields[key] = raw.strip()
        else:
            fields[key] = _to_number(raw)
    code = fields.get("code")
    name = fields.get("name")
    if not code and not name:
        return None
    return StockMetric(
        code=str(code or "").strip(),
        name=str(name or "").strip(),
        sector=fields.get("sector"),
        industry=fields.get("industry"),
        price=fields.get("price"),
        change_rate=fields.get("change_rate"),
        wsma120=fields.get("wsma120"),
        slope120=fields.get("slope120"),
        curv120=fields.get("curv120"),
        z180=fields.get("z180"),
        align=fields.get("align"),
        momentum=fields.get("momentum"),
        escore=fields.get("escore"),
    )


def _map_industry_row(
    headers: list[str], values: list[str], default_rank: int
) -> Optional[LeadingIndustry]:
    fields: dict[str, Any] = {}
    for header, raw in zip(headers, values):
        key = _INDUSTRY_HEADER_HINTS.get(_normalize_header(header))
        if key is None:
            continue
        if key == "industry":
            fields[key] = raw.strip()
        elif key == "member_count" or key == "rank":
            fields[key] = _to_int(raw)
        else:
            fields[key] = _to_number(raw)
    industry = fields.get("industry")
    if not industry:
        return None
    return LeadingIndustry(
        industry=industry,
        avg_return=fields.get("avg_return"),
        avg_escore=fields.get("avg_escore"),
        member_count=fields.get("member_count"),
        rank=fields.get("rank") or default_rank,
    )


def _section_title(table: Tag, default: str) -> str:
    for parent in (table.find_parent("section"), table.find_parent("div")):
        if parent is None:
            continue
        heading = parent.find(["h1", "h2", "h3", "h4"])
        if heading and heading.get_text(strip=True):
            return heading.get_text(strip=True)
    caption = table.find("caption")
    if caption and caption.get_text(strip=True):
        return caption.get_text(strip=True)
    return default


def _generic_section(table: Tag, headers: list[str], idx: int) -> DashboardSection:
    rows: list[dict[str, Any]] = []
    for values in _table_rows(table, len(headers)):
        rows.append({h: v for h, v in zip(headers, values)})
    title = _section_title(table, default=f"표 {idx + 1}")
    key = re.sub(r"\W+", "_", title).strip("_").lower() or f"table_{idx}"
    return DashboardSection(key=key, title=title, kind="table", columns=headers, rows=rows)


def _value_after_node(node: Tag) -> Optional[str]:
    for sibling in node.next_siblings:
        if isinstance(sibling, NavigableString):
            text = str(sibling).strip()
            if text:
                return text
            continue
        if isinstance(sibling, Tag):
            if sibling.name == "br":
                continue
            text = sibling.get_text(" ", strip=True)
            if text:
                return text
    return None


def _node_label(node: Tag) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                parts.append(text)
        elif isinstance(child, Tag) and child.name not in ("i", "svg", "img"):
            text = child.get_text(" ", strip=True)
            if text:
                parts.append(text)
    return " ".join(parts).strip()


def _matches_card(node: Tag) -> bool:
    classes = node.get("class") or []
    return "card" in classes


def _has_card_ancestor(node: Tag) -> bool:
    for parent in node.parents:
        if isinstance(parent, Tag) and _matches_card(parent):
            return True
    return False


def _card_title(card: Tag, default: str) -> str:
    for selector in (".card-header", ".card-title", "h1", "h2", "h3", "h4", "h5", "h6"):
        node = card.select_one(selector)
        if node:
            text = node.get_text(" ", strip=True)
            if text:
                return text
    return default


def _collect_card_rows(card: Tag) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for span in card.find_all("span", class_="term-help"):
        label = _node_label(span)
        value = _value_after_node(span)
        if label and value is not None:
            rows.append({"label": label, "value": value})

    for small in card.select("small.text-muted"):
        label = _node_label(small)
        if not label:
            continue
        value: Optional[str] = None
        for sibling in small.next_siblings:
            if isinstance(sibling, Tag) and sibling.name in ("strong", "b"):
                value = sibling.get_text(" ", strip=True)
                break
        if value:
            rows.append({"label": label, "value": value})

    return rows


def _parse_card_layout(soup: BeautifulSoup) -> list[DashboardSection]:
    sections: list[DashboardSection] = []
    cards = [n for n in soup.find_all("div") if isinstance(n, Tag) and _matches_card(n)]
    top_level = [c for c in cards if not _has_card_ancestor(c)]

    for idx, card in enumerate(top_level):
        rows = _collect_card_rows(card)
        title = _card_title(card, default=f"카드 {idx + 1}")
        key = card.get("id") or re.sub(r"\W+", "_", title).strip("_").lower() or f"card_{idx}"
        sections.append(
            DashboardSection(
                key=key,
                title=title,
                kind="card",
                columns=["label", "value"] if rows else [],
                rows=rows,
                extras={"html": card.decode_contents()},
            )
        )
    return sections


def _extract_full_page_section(soup: BeautifulSoup) -> Optional[DashboardSection]:
    for selector in ("main", "div.container", "div.container-fluid", "body"):
        node = soup.select_one(selector)
        if node and node.decode_contents().strip():
            return DashboardSection(
                key="full_page",
                title="산업군 분석 전체",
                kind="raw_html",
                extras={"html": node.decode_contents()},
            )
    return None


_URL_ATTR_TARGETS = (
    ("a", "href"),
    ("link", "href"),
    ("script", "src"),
    ("img", "src"),
    ("source", "src"),
    ("iframe", "src"),
    ("form", "action"),
    ("video", "src"),
    ("audio", "src"),
)


def _absolutize_urls(soup: BeautifulSoup, base_url: str) -> None:
    base_tag = soup.find("base")
    effective_base = (base_tag.get("href") if base_tag and base_tag.get("href") else base_url)

    for tag, attr in _URL_ATTR_TARGETS:
        for element in soup.find_all(tag):
            url = element.get(attr)
            if not url:
                continue
            if url.startswith(("data:", "javascript:", "mailto:", "tel:", "#")):
                continue
            element[attr] = urljoin(effective_base, url)

    for element in soup.find_all(attrs={"srcset": True}):
        parts = []
        for piece in element["srcset"].split(","):
            piece = piece.strip()
            if not piece:
                continue
            url, _, descriptor = piece.partition(" ")
            absolute = urljoin(effective_base, url)
            parts.append(f"{absolute} {descriptor}".strip())
        element["srcset"] = ", ".join(parts)


def _extract_full_document_section(
    soup: BeautifulSoup, base_url: Optional[str]
) -> Optional[DashboardSection]:
    if not base_url:
        return None
    if not soup.find("html") and not soup.find("body"):
        return None
    _absolutize_urls(soup, base_url)
    return DashboardSection(
        key="full_html_document",
        title="원본 HTML 문서(iframe 용)",
        kind="full_html_document",
        extras={"html": str(soup), "base_url": base_url},
    )


def _try_parse_inline_json(soup: BeautifulSoup) -> Optional[dict[str, Any]]:
    for script_id in (
        "__DASHBOARD_DATA__",
        "__NEXT_DATA__",
        "dashboard-data",
        "__SECTORS_DATA__",
    ):
        node = soup.find("script", id=script_id)
        if node and node.string:
            try:
                return json.loads(node.string)
            except json.JSONDecodeError:
                continue
    return None


def parse_sectors_html(
    html: str, base_url: Optional[str] = None
) -> tuple[list[StockMetric], list[LeadingIndustry], list[DashboardSection]]:
    soup = BeautifulSoup(html, "html.parser")

    inline = _try_parse_inline_json(soup)
    if isinstance(inline, dict) and "stock_metrics" in inline:
        metrics = [StockMetric(**row) for row in inline.get("stock_metrics", [])]
        industries = [LeadingIndustry(**row) for row in inline.get("leading_industries", [])]
        sections = [DashboardSection(**row) for row in inline.get("sections", [])]
        return metrics, industries, sections

    metrics: list[StockMetric] = []
    industries: list[LeadingIndustry] = []
    sections: list[DashboardSection] = []

    for idx, table in enumerate(soup.find_all("table")):
        headers = _table_headers(table)
        if not headers:
            continue
        kind = _classify_table(headers)
        if kind == "stock_metric":
            for values in _table_rows(table, len(headers)):
                metric = _map_metric_row(headers, values)
                if metric is not None:
                    metrics.append(metric)
        elif kind == "leading_industry":
            rank_seq = 0
            for values in _table_rows(table, len(headers)):
                rank_seq += 1
                row = _map_industry_row(headers, values, default_rank=rank_seq)
                if row is not None:
                    industries.append(row)
        else:
            sections.append(_generic_section(table, headers, idx))

    sections.extend(_parse_card_layout(soup))

    full_page = _extract_full_page_section(soup)
    if full_page is not None:
        sections.append(full_page)

    full_document = _extract_full_document_section(soup, base_url)
    if full_document is not None:
        sections.append(full_document)

    return metrics, industries, sections

"""KR A.2 — 사용자 라벨 vs LLM v2 결과 비교 리포트.

사용자가 tests/quality/kr_a2_labels/<TICKER>_labels.json에 직접 라벨링한 30~50건과
event_enrichments DB의 v2 분류 결과를 비교한다.

목표:
- 분류 정확도(type 일치율) ≥ 80%
- 중요도 일치율(±1 범위) ≥ 70%
- Pearson 상관계수 출력

실행:
    python tests/quality/validate_kr_a2.py --ticker AAPL --ticker GOOG

종료 코드:
    0 — 모든 ticker가 임계값 통과
    1 — 임계값 미달 ticker 1개 이상
"""
import argparse
import asyncio
import json
import logging
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# 프로젝트 루트를 import path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select

from app.domains.history_agent.infrastructure.orm.event_enrichment_orm import EventEnrichmentOrm
from app.infrastructure.database.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validate_kr_a2")

LABELS_DIR = Path(__file__).parent / "kr_a2_labels"

CLASSIFICATION_THRESHOLD = 0.80
IMPORTANCE_THRESHOLD = 0.70


def load_labels(ticker: str) -> List[Dict[str, Any]]:
    path = LABELS_DIR / f"{ticker}_labels.json"
    if not path.exists():
        logger.error("라벨 파일이 없습니다: %s", path)
        return []
    with path.open() as f:
        return json.load(f)


async def fetch_v2_results(ticker: str, detail_hashes: List[str]) -> Dict[str, EventEnrichmentOrm]:
    """v2 분류 결과를 detail_hash로 매핑."""
    async with AsyncSessionLocal() as session:
        stmt = select(EventEnrichmentOrm).where(
            EventEnrichmentOrm.ticker == ticker,
            EventEnrichmentOrm.detail_hash.in_(detail_hashes),
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

    # detail_hash별 v2 행 우선, 없으면 v1으로 fallback
    by_hash: Dict[str, EventEnrichmentOrm] = {}
    for row in rows:
        existing = by_hash.get(row.detail_hash)
        if not existing or row.classifier_version == "v2":
            by_hash[row.detail_hash] = row
    return by_hash


def pearson_correlation(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) < 2 or len(ys) < 2:
        return None
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


async def validate_ticker(ticker: str) -> Dict[str, Any]:
    labels = load_labels(ticker)
    if not labels:
        return {"ticker": ticker, "status": "no_labels", "passed": False}

    detail_hashes = [lab["detail_hash"] for lab in labels]
    db_map = await fetch_v2_results(ticker, detail_hashes)

    matched = 0
    classification_correct = 0
    importance_close = 0  # ±1 범위 일치
    confusion = defaultdict(Counter)
    importance_pairs: List[tuple] = []
    type_errors = []

    for label in labels:
        h = label["detail_hash"]
        row = db_map.get(h)
        if not row:
            continue
        matched += 1

        # v2 type — reclassified_type 우선, 없으면 event_type
        v2_type = row.reclassified_type or row.event_type
        human_type = label["type"]

        confusion[human_type][v2_type] += 1
        if v2_type == human_type:
            classification_correct += 1
        else:
            type_errors.append({
                "date": label["date"],
                "human": human_type,
                "v2": v2_type,
                "excerpt": (label.get("detail_excerpt") or "")[:80],
            })

        v2_score_1to5 = row.importance_score_1to5
        if v2_score_1to5 is None and row.importance_score is not None:
            # v1 fallback — 0~1 → 1~5 변환
            v2_score_1to5 = max(1, min(5, math.ceil(row.importance_score * 5)))

        if v2_score_1to5 is not None:
            human_score = label["human_importance_1to5"]
            importance_pairs.append((human_score, v2_score_1to5))
            if abs(human_score - v2_score_1to5) <= 1:
                importance_close += 1

    if matched == 0:
        return {"ticker": ticker, "status": "no_matches", "passed": False, "labels": len(labels)}

    classification_rate = classification_correct / matched
    importance_rate = importance_close / max(len(importance_pairs), 1)

    correlation = pearson_correlation(
        [float(p[0]) for p in importance_pairs],
        [float(p[1]) for p in importance_pairs],
    )

    passed = (
        classification_rate >= CLASSIFICATION_THRESHOLD
        and importance_rate >= IMPORTANCE_THRESHOLD
    )

    return {
        "ticker": ticker,
        "status": "ok",
        "passed": passed,
        "labels": len(labels),
        "matched": matched,
        "classification_correct": classification_correct,
        "classification_rate": classification_rate,
        "importance_close": importance_close,
        "importance_total": len(importance_pairs),
        "importance_rate": importance_rate,
        "correlation": correlation,
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "type_errors": type_errors[:10],  # 상위 10건만 출력
    }


def print_report(report: Dict[str, Any]) -> None:
    ticker = report["ticker"]
    print(f"\n=== {ticker} 검증 리포트 ===")
    if report["status"] != "ok":
        print(f"  status: {report['status']}")
        return

    cls_rate = report["classification_rate"]
    imp_rate = report["importance_rate"]
    corr = report["correlation"]
    cls_mark = "✓" if cls_rate >= CLASSIFICATION_THRESHOLD else "✗"
    imp_mark = "✓" if imp_rate >= IMPORTANCE_THRESHOLD else "✗"

    print(f"  라벨 매칭: {report['matched']} / {report['labels']}")
    print(f"  {cls_mark} 분류 정확도: {cls_rate:.1%} (목표 {CLASSIFICATION_THRESHOLD:.0%})")
    print(f"  {imp_mark} 중요도 ±1 일치율: {imp_rate:.1%} (목표 {IMPORTANCE_THRESHOLD:.0%})")
    print(f"  Pearson 상관: {corr:.2f}" if corr is not None else "  Pearson: N/A")

    if report["type_errors"]:
        print("  주요 오분류:")
        for err in report["type_errors"]:
            print(f"    {err['date']} 사용자={err['human']:22} v2={err['v2']:22} {err['excerpt']}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", action="append", required=True, help="검증할 ticker (반복)")
    args = parser.parse_args()

    reports = []
    for ticker in args.ticker:
        report = await validate_ticker(ticker)
        reports.append(report)
        print_report(report)

    all_passed = all(r["passed"] for r in reports)
    failed = [r["ticker"] for r in reports if not r["passed"]]
    print(f"\n총 {len(reports)}개 ticker — 통과 {len(reports) - len(failed)}, 실패 {len(failed)}")
    if failed:
        print(f"실패: {', '.join(failed)}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())

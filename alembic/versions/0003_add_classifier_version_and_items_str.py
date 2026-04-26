"""add classifier_version, importance_score_1to5, items_str to event_enrichments

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-26

KR A.1/A.2/A.4: 공시 분류 v2 시스템 도입
- classifier_version: v1/v2 행 동시 보유. UK에 포함하여 동일 (ticker, date, type, detail_hash)에
  대해 v1과 v2를 별도 행으로 저장 가능. 기존 행은 모두 v1으로 백필.
- importance_score_1to5: 사용자 OKR 1~5점 척도. 기존 importance_score(0~1 float)는 v1으로 유지.
- items_str: SEC 8-K raw Item 코드(예: "1.01,9.01"). KR A.1 빈도 분석 데이터.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) 새 컬럼 추가 (모두 NULL 허용으로 시작)
    op.add_column(
        "event_enrichments",
        sa.Column("importance_score_1to5", sa.Integer(), nullable=True),
    )
    op.add_column(
        "event_enrichments",
        sa.Column("items_str", sa.String(50), nullable=True),
    )
    op.add_column(
        "event_enrichments",
        sa.Column("reclassified_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "event_enrichments",
        sa.Column("classifier_version", sa.String(10), nullable=True),
    )

    # 2) 기존 행 모두 classifier_version='v1' 백필 후 NOT NULL 제약 적용
    op.execute("UPDATE event_enrichments SET classifier_version = 'v1' WHERE classifier_version IS NULL")
    op.alter_column(
        "event_enrichments",
        "classifier_version",
        existing_type=sa.String(10),
        nullable=False,
    )

    # 3) UK 재구성 — classifier_version 포함
    op.drop_constraint("uq_event_enrichments_key", "event_enrichments", type_="unique")
    op.create_unique_constraint(
        "uq_event_enrichments_key",
        "event_enrichments",
        ["ticker", "event_date", "event_type", "detail_hash", "classifier_version"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_event_enrichments_key", "event_enrichments", type_="unique")
    op.create_unique_constraint(
        "uq_event_enrichments_key",
        "event_enrichments",
        ["ticker", "event_date", "event_type", "detail_hash"],
    )
    op.drop_column("event_enrichments", "classifier_version")
    op.drop_column("event_enrichments", "reclassified_type")
    op.drop_column("event_enrichments", "items_str")
    op.drop_column("event_enrichments", "importance_score_1to5")

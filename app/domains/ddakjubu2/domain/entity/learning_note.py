from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class StockInsight:
    stock_name: str
    ticker: str
    investment_view: str
    key_claims: List[str]
    supporting_evidence: List[str]


@dataclass
class LearningNote:
    video_id: str
    video_title: str
    channel_name: str
    program_category: str
    published_at: datetime
    learned_at: datetime
    summary: str
    stock_insights: List[StockInsight] = field(default_factory=list)

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class BusinessOverview:
    summary: str
    revenue_sources: list[str] = field(default_factory=list)
    source: str = "llm_only"  # "rag_summary" | "llm_only" | "asset_llm_only"
    founding_story: Optional[str] = None
    business_model: Optional[str] = None

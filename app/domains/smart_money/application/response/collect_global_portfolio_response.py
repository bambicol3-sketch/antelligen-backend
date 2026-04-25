from pydantic import BaseModel


class InvestorCollectResult(BaseModel):
    investor_name: str
    reported_at: str
    total_holdings: int
    new_positions: int
    closed_positions: int
    skipped: bool
    reason: str | None = None


class CollectGlobalPortfolioResponse(BaseModel):
    results: list[InvestorCollectResult]
    total_saved: int

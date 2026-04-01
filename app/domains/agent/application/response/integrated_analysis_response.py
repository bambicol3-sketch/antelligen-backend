from pydantic import BaseModel


class IntegratedAnalysisResponse(BaseModel):
    ticker: str
    query: str
    overall_signal: str  # bullish | bearish | neutral
    confidence: float
    summary: str
    key_points: list[str]
    sub_results: list[dict]
    execution_time_ms: int

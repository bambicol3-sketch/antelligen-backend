from dataclasses import dataclass
from datetime import date


@dataclass
class KrPortfolioHolding:
    investor_name: str
    investor_type: str  # PENSION | ASSET_MANAGER | INDIVIDUAL
    stock_code: str
    stock_name: str
    shares_held: int
    ownership_ratio: float  # 지분율 (%)
    change_type: str  # NEW | INCREASED | DECREASED | CLOSED
    reported_at: date

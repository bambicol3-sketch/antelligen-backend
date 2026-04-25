from dataclasses import dataclass


@dataclass(frozen=True)
class StockName:
    value: str

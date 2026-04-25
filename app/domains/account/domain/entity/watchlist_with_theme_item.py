from dataclasses import dataclass


@dataclass
class WatchlistWithThemeItem:
    stock_code: str
    stock_name: str
    theme_name: str

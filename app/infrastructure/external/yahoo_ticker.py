"""yfinance가 요구하는 티커 표기 정규화.

사용자/프론트가 `IXIC`, `GSPC`, `KS11` 같은 bare 심볼을 보낼 때 yfinance는
`^` prefix가 없으면 404로 응답한다. 입력 경계에서 이 매핑을 적용해
downstream 전 구간이 canonical 표기(`^IXIC` 등)를 받도록 한다.
"""

from typing import Dict

INDEX_TICKER_MAP: Dict[str, str] = {
    "IXIC": "^IXIC",
    "DJI": "^DJI",
    "INDU": "^DJI",
    "GSPC": "^GSPC",
    "SPX": "^GSPC",
    "RUT": "^RUT",
    "VIX": "^VIX",
    "FTSE": "^FTSE",
    "N225": "^N225",
    "HSI": "^HSI",
    "GDAXI": "^GDAXI",
    "KS11": "^KS11",
    "KQ11": "^KQ11",
    "KS200": "^KS200",
    "SSEC": "000001.SS",
    "TNX": "^TNX",
}


def normalize_yfinance_ticker(ticker: str) -> str:
    if ticker.startswith("^"):
        return ticker
    if ticker.isdigit() and len(ticker) == 6:
        return f"{ticker}.KS"
    return INDEX_TICKER_MAP.get(ticker, ticker)

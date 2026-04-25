import asyncio
import logging
import os
from datetime import date

from app.domains.smart_money.application.port.out.krx_investor_flow_port import KrxInvestorFlowPort
from app.domains.smart_money.domain.entity.investor_flow import InvestorFlow, InvestorType

logger = logging.getLogger(__name__)

_INVESTOR_MAP: dict[InvestorType, str] = {
    InvestorType.FOREIGN: "외국인",
    InvestorType.INSTITUTION: "기관합계",
    InvestorType.INDIVIDUAL: "개인",
}

_MARKETS = ["KOSPI", "KOSDAQ"]

# pykrx 컬럼명 (버전별 차이 대응)
_COL_STOCK_NAME = "종목명"
_COL_NET_BUY_VOLUME = "순매수거래량"
_COL_NET_BUY_AMOUNT = "순매수거래대금"


def _set_krx_credentials(krx_id: str, krx_pw: str) -> None:
    if krx_id:
        os.environ["KRX_ID"] = krx_id
    if krx_pw:
        os.environ["KRX_PW"] = krx_pw


def _fetch_sync(date_str: str, krx_id: str, krx_pw: str) -> list[InvestorFlow]:
    """동기 블로킹 pykrx 호출 — asyncio.to_thread()로 실행된다."""
    _set_krx_credentials(krx_id, krx_pw)

    from pykrx import stock as krx_stock

    target = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
    flows: list[InvestorFlow] = []

    for investor_type, investor_name in _INVESTOR_MAP.items():
        for market in _MARKETS:
            try:
                df = krx_stock.get_market_net_purchases_of_equities(
                    date_str, date_str, market, investor_name
                )
                if df is None or df.empty:
                    logger.warning(
                        "[krx_client] %s %s %s — 빈 응답 (KRX 인증 확인 필요)",
                        date_str, market, investor_name,
                    )
                    continue

                for stock_code, row in df.iterrows():
                    stock_name = str(row.get(_COL_STOCK_NAME, "")).strip()
                    if not stock_name:
                        continue

                    net_buy_volume = int(row.get(_COL_NET_BUY_VOLUME, 0))
                    net_buy_amount = int(row.get(_COL_NET_BUY_AMOUNT, 0))

                    flows.append(
                        InvestorFlow(
                            date=target,
                            investor_type=investor_type,
                            stock_code=str(stock_code).zfill(6),
                            stock_name=stock_name,
                            net_buy_amount=net_buy_amount,
                            net_buy_volume=net_buy_volume,
                        )
                    )
            except Exception as exc:
                logger.warning(
                    "[krx_client] %s %s %s 수집 실패: %s",
                    date_str, market, investor_name, exc,
                )
                continue

    return flows


class KrxInvestorFlowClient(KrxInvestorFlowPort):

    def __init__(self, krx_id: str = "", krx_pw: str = ""):
        self._krx_id = krx_id
        self._krx_pw = krx_pw

    async def fetch(self, target_date: date) -> list[InvestorFlow]:
        if not self._krx_id or not self._krx_pw:
            logger.warning(
                "[krx_client] KRX 인증 정보 없음 — .env에 KRX_ID, KRX_PW를 설정하세요. "
                "data.krx.co.kr에서 무료 회원가입 후 발급 가능합니다."
            )

        date_str = target_date.strftime("%Y%m%d")
        logger.info("[krx_client] %s 순매수 데이터 fetch 시작", date_str)

        flows = await asyncio.to_thread(_fetch_sync, date_str, self._krx_id, self._krx_pw)
        logger.info("[krx_client] %s 총 %d 건 수집", date_str, len(flows))
        return flows

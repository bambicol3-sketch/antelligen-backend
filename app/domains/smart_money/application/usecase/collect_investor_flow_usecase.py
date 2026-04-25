import logging
from datetime import date, timedelta

from app.domains.smart_money.application.port.out.investor_flow_repository_port import InvestorFlowRepositoryPort
from app.domains.smart_money.application.port.out.krx_investor_flow_port import KrxInvestorFlowPort
from app.domains.smart_money.application.response.collect_investor_flow_response import CollectInvestorFlowResponse

logger = logging.getLogger(__name__)


class CollectInvestorFlowUseCase:
    def __init__(
        self,
        krx_port: KrxInvestorFlowPort,
        repository: InvestorFlowRepositoryPort,
    ):
        self._krx_port = krx_port
        self._repository = repository

    async def execute(self, target_date: date | None = None) -> CollectInvestorFlowResponse:
        if target_date is None:
            target_date = date.today() - timedelta(days=1)  # 전일 기준

        date_str = target_date.strftime("%Y-%m-%d")
        logger.info("[smart_money] %s 투자자 순매수 데이터 수집 시작", date_str)

        flows = await self._krx_port.fetch(target_date)
        if not flows:
            logger.warning("[smart_money] %s 수집된 데이터 없음 (휴장일 가능성)", date_str)
            return CollectInvestorFlowResponse(
                target_date=date_str,
                total_collected=0,
                skipped_duplicates=0,
            )

        to_save = []
        skipped = 0
        for flow in flows:
            already = await self._repository.exists(
                target_date, flow.investor_type.value, flow.stock_code
            )
            if already:
                skipped += 1
            else:
                to_save.append(flow)

        saved = await self._repository.save_batch(to_save)
        logger.info(
            "[smart_money] %s 수집 완료 — 저장: %d, 중복 스킵: %d",
            date_str, saved, skipped,
        )
        return CollectInvestorFlowResponse(
            target_date=date_str,
            total_collected=saved,
            skipped_duplicates=skipped,
        )

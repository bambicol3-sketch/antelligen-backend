import logging

from app.domains.smart_money.application.port.out.global_portfolio_fetch_port import GlobalPortfolioFetchPort
from app.domains.smart_money.application.port.out.global_portfolio_repository_port import GlobalPortfolioRepositoryPort
from app.domains.smart_money.application.response.collect_global_portfolio_response import (
    CollectGlobalPortfolioResponse,
    InvestorCollectResult,
)
from app.domains.smart_money.domain.service.global_portfolio_domain_service import GlobalPortfolioDomainService

logger = logging.getLogger(__name__)

# 수집 대상 투자자 — CIK는 SEC EDGAR 고유 식별자
INVESTOR_CIK_MAP: dict[str, str] = {
    # 전설적 투자자
    "Warren Buffett":        "0001067983",  # Berkshire Hathaway Inc
    "Michael Burry":         "0001326110",  # Scion Asset Management LLC
    "George Soros":          "0001029160",  # Soros Fund Management LLC
    "Carl Icahn":            "0000813672",  # Icahn Capital Management LP
    "Seth Klarman":          "0001061768",  # Baupost Group LLC
    "David Einhorn":         "0001079114",  # Greenlight Capital Inc
    # 헤지펀드 매니저
    "Bill Ackman":           "0001336528",  # Pershing Square Capital Management
    "David Tepper":          "0001418814",  # Appaloosa Management LP
    "Ray Dalio":             "0001350694",  # Bridgewater Associates LP
    "Stan Druckenmiller":    "0001536411",  # Duquesne Family Office LLC
    "Dan Loeb":              "0001040273",  # Third Point LLC
    "Steve Cohen":           "0001603466",  # Point72 Asset Management LP
    # 퀀트·대형 운용사
    "Ken Griffin":           "0001423689",  # Citadel Advisors LLC
    "Israel Englander":      "0001273931",  # Millennium Management LLC
    "Renaissance Technologies": "0001037389",  # Renaissance Technologies LLC
    "Two Sigma":             "0001440822",  # Two Sigma Investments LP
    "D.E. Shaw":             "0001009207",  # D.E. Shaw & Co.
    # 성장주 중심
    "Cathie Wood":           "0001799590",  # ARK Investment Management LLC
    "Tiger Global":          "0001167483",  # Tiger Global Management LLC
}


class CollectGlobalPortfolioUseCase:
    def __init__(
        self,
        fetch_port: GlobalPortfolioFetchPort,
        repository: GlobalPortfolioRepositoryPort,
    ):
        self._fetch_port = fetch_port
        self._repository = repository

    async def execute(self) -> CollectGlobalPortfolioResponse:
        results: list[InvestorCollectResult] = []
        total_saved = 0

        for investor_name, cik in INVESTOR_CIK_MAP.items():
            logger.info("[global_portfolio] %s (CIK %s) 수집 시작", investor_name, cik)
            try:
                result = await self._collect_one(investor_name, cik)
                results.append(result)
                total_saved += result.total_holdings
            except Exception as exc:
                logger.exception("[global_portfolio] %s 수집 실패: %s", investor_name, exc)
                results.append(InvestorCollectResult(
                    investor_name=investor_name,
                    reported_at="",
                    total_holdings=0,
                    new_positions=0,
                    closed_positions=0,
                    skipped=True,
                    reason=str(exc),
                ))

        return CollectGlobalPortfolioResponse(results=results, total_saved=total_saved)

    async def _collect_one(self, investor_name: str, cik: str) -> InvestorCollectResult:
        # 1. SEC EDGAR에서 최신 13F 데이터 수집
        current_holdings = await self._fetch_port.fetch_latest(investor_name, cik)
        if not current_holdings:
            return InvestorCollectResult(
                investor_name=investor_name,
                reported_at="",
                total_holdings=0,
                new_positions=0,
                closed_positions=0,
                skipped=True,
                reason="13F 데이터 없음",
            )

        reported_at = current_holdings[0].reported_at

        # 2. 이미 수집된 분기면 스킵
        if await self._repository.exists_for_period(investor_name, reported_at):
            logger.info("[global_portfolio] %s %s — 이미 수집됨, 스킵", investor_name, reported_at)
            return InvestorCollectResult(
                investor_name=investor_name,
                reported_at=str(reported_at),
                total_holdings=0,
                new_positions=0,
                closed_positions=0,
                skipped=True,
                reason="이미 수집된 분기",
            )

        # 3. 직전 분기 데이터 조회
        previous_holdings = await self._repository.find_previous_holdings(investor_name, reported_at)
        previous_map = {h.cusip: h.shares for h in previous_holdings}

        # 4. 포트폴리오 비중 계산
        active_holdings = GlobalPortfolioDomainService.compute_portfolio_weights(current_holdings)

        # 5. change_type 계산
        current_cusips: set[str] = set()
        for h in active_holdings:
            current_cusips.add(h.cusip)
            prev_shares = previous_map.get(h.cusip)
            h.change_type = GlobalPortfolioDomainService.compute_change_type(h.shares, prev_shares)

        # 6. CLOSED 포지션 생성
        closed = GlobalPortfolioDomainService.compute_closed_positions(
            current_cusips, previous_holdings, reported_at
        )

        all_to_save = active_holdings + closed

        # 7. 저장
        saved = await self._repository.save_batch(all_to_save)
        new_count = sum(1 for h in active_holdings if h.change_type.value == "NEW")
        logger.info(
            "[global_portfolio] %s %s — 저장 %d건 (신규 %d, 청산 %d)",
            investor_name, reported_at, saved, new_count, len(closed),
        )

        return InvestorCollectResult(
            investor_name=investor_name,
            reported_at=str(reported_at),
            total_holdings=saved,
            new_positions=new_count,
            closed_positions=len(closed),
            skipped=False,
        )

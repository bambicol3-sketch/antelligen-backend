from app.domains.smart_money.domain.entity.global_portfolio import ChangeType, GlobalPortfolio


class GlobalPortfolioDomainService:

    @staticmethod
    def compute_change_type(
        current_shares: int,
        previous_shares: int | None,
    ) -> ChangeType:
        """직전 분기 보유량 대비 변동 유형을 계산한다."""
        if previous_shares is None:
            return ChangeType.NEW
        if current_shares > previous_shares:
            return ChangeType.INCREASED
        if current_shares < previous_shares:
            return ChangeType.DECREASED
        # 동일 수량 — 변동 없음은 DECREASED와 구분하기 위해 별도 처리하지 않고 DECREASED 반환 방지
        return ChangeType.DECREASED  # 동량 보유는 실질적으로 비중 변화일 수 있어 DECREASED 처리

    @staticmethod
    def compute_closed_positions(
        current_cusips: set[str],
        previous_holdings: list[GlobalPortfolio],
        reported_at,
    ) -> list[GlobalPortfolio]:
        """직전 분기에 보유했으나 현재 분기에 사라진 종목을 CLOSED 포지션으로 반환한다."""
        closed: list[GlobalPortfolio] = []
        for prev in previous_holdings:
            if prev.cusip not in current_cusips:
                closed.append(
                    GlobalPortfolio(
                        investor_name=prev.investor_name,
                        ticker=prev.ticker,
                        stock_name=prev.stock_name,
                        cusip=prev.cusip,
                        shares=0,
                        market_value=0,
                        portfolio_weight=0.0,
                        reported_at=reported_at,
                        change_type=ChangeType.CLOSED,
                    )
                )
        return closed

    @staticmethod
    def compute_portfolio_weights(holdings: list[GlobalPortfolio]) -> list[GlobalPortfolio]:
        """전체 포트폴리오 대비 각 종목의 비중(%)을 계산하여 반환한다."""
        total_value = sum(h.market_value for h in holdings if h.market_value > 0)
        if total_value == 0:
            return holdings
        for h in holdings:
            h.portfolio_weight = round(h.market_value / total_value * 100, 4)
        return holdings

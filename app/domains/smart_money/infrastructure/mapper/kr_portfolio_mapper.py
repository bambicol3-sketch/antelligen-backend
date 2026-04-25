from app.domains.smart_money.domain.entity.kr_portfolio import KrPortfolioHolding
from app.domains.smart_money.infrastructure.orm.kr_portfolio_orm import KrPortfolioOrm


class KrPortfolioMapper:

    @staticmethod
    def to_entity(orm: KrPortfolioOrm) -> KrPortfolioHolding:
        return KrPortfolioHolding(
            investor_name=orm.investor_name,
            investor_type=orm.investor_type,
            stock_code=orm.stock_code,
            stock_name=orm.stock_name,
            shares_held=orm.shares_held,
            ownership_ratio=orm.ownership_ratio,
            change_type=orm.change_type,
            reported_at=orm.reported_at,
        )

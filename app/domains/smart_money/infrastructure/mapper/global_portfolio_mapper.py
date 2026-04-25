from app.domains.smart_money.domain.entity.global_portfolio import ChangeType, GlobalPortfolio
from app.domains.smart_money.infrastructure.orm.global_portfolio_orm import GlobalPortfolioOrm


class GlobalPortfolioMapper:

    @staticmethod
    def to_orm(p: GlobalPortfolio) -> GlobalPortfolioOrm:
        return GlobalPortfolioOrm(
            investor_name=p.investor_name,
            ticker=p.ticker,
            stock_name=p.stock_name,
            cusip=p.cusip,
            shares=p.shares,
            market_value=p.market_value,
            portfolio_weight=p.portfolio_weight,
            reported_at=p.reported_at,
            change_type=p.change_type.value,
        )

    @staticmethod
    def to_entity(orm: GlobalPortfolioOrm) -> GlobalPortfolio:
        return GlobalPortfolio(
            portfolio_id=orm.id,
            investor_name=orm.investor_name,
            ticker=orm.ticker,
            stock_name=orm.stock_name,
            cusip=orm.cusip,
            shares=orm.shares,
            market_value=orm.market_value,
            portfolio_weight=orm.portfolio_weight,
            reported_at=orm.reported_at,
            change_type=ChangeType(orm.change_type),
            collected_at=orm.collected_at,
        )

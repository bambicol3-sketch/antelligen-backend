from app.domains.smart_money.domain.entity.investor_flow import InvestorFlow, InvestorType
from app.domains.smart_money.infrastructure.orm.investor_flow_orm import InvestorFlowOrm


class InvestorFlowMapper:

    @staticmethod
    def to_orm(flow: InvestorFlow) -> InvestorFlowOrm:
        return InvestorFlowOrm(
            date=flow.date,
            investor_type=flow.investor_type.value,
            stock_code=flow.stock_code,
            stock_name=flow.stock_name,
            net_buy_amount=flow.net_buy_amount,
            net_buy_volume=flow.net_buy_volume,
        )

    @staticmethod
    def to_entity(orm: InvestorFlowOrm) -> InvestorFlow:
        return InvestorFlow(
            flow_id=orm.id,
            date=orm.date,
            investor_type=InvestorType(orm.investor_type),
            stock_code=orm.stock_code,
            stock_name=orm.stock_name,
            net_buy_amount=orm.net_buy_amount,
            net_buy_volume=orm.net_buy_volume,
            collected_at=orm.collected_at,
        )

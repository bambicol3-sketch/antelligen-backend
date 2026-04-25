from dataclasses import dataclass


@dataclass
class AccumulatedFlow:
    stock_code: str
    stock_name: str
    total_net_buy: int


@dataclass
class ConcentratedStock:
    stock_code: str
    stock_name: str
    foreign_net_buy: int
    institution_net_buy: int
    total_net_buy: int
    concentration_score: float


class SmartMoneyDomainService:

    @staticmethod
    def compute_concentration_score(
        foreign_amount: int,
        institution_amount: int,
        max_foreign: int,
        max_institution: int,
    ) -> float:
        """외국인·기관 순매수를 각각 정규화한 뒤 평균하여 0~100 점수를 반환한다."""
        f_score = foreign_amount / max_foreign if max_foreign > 0 else 0.0
        i_score = institution_amount / max_institution if max_institution > 0 else 0.0
        return round((f_score + i_score) / 2 * 100, 2)

    @staticmethod
    def compute_concentrated_stocks(
        foreign_flows: list[AccumulatedFlow],
        institution_flows: list[AccumulatedFlow],
        limit: int,
    ) -> list[ConcentratedStock]:
        """외국인·기관 동시 순매수 종목 교집합을 집중 매수 점수 내림차순으로 반환한다."""
        foreign_map = {f.stock_code: f for f in foreign_flows if f.total_net_buy > 0}
        institution_map = {f.stock_code: f for f in institution_flows if f.total_net_buy > 0}

        common_codes = set(foreign_map) & set(institution_map)
        if not common_codes:
            return []

        max_foreign = max(f.total_net_buy for f in foreign_map.values()) or 1
        max_institution = max(f.total_net_buy for f in institution_map.values()) or 1

        results: list[ConcentratedStock] = []
        for code in common_codes:
            f = foreign_map[code]
            i = institution_map[code]
            score = SmartMoneyDomainService.compute_concentration_score(
                f.total_net_buy, i.total_net_buy, max_foreign, max_institution
            )
            results.append(ConcentratedStock(
                stock_code=code,
                stock_name=f.stock_name,
                foreign_net_buy=f.total_net_buy,
                institution_net_buy=i.total_net_buy,
                total_net_buy=f.total_net_buy + i.total_net_buy,
                concentration_score=score,
            ))

        results.sort(key=lambda x: x.concentration_score, reverse=True)
        return results[:limit]

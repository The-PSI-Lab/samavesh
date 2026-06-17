from dataclasses import dataclass
from typing import List


@dataclass
class CashFlowRow:
    year: int
    investment: float
    benefit: float
    net_cash_flow: float
    cumulative: float


def build_cashflow(tci, net_annual_benefit, plant_life_years) -> List[CashFlowRow]:
    tci = float(tci)
    net_annual_benefit = float(net_annual_benefit)
    plant_life_years = int(plant_life_years)

    rows = []
    cumulative = 0.0
    for year in range(0, plant_life_years + 1):
        if year == 0:
            investment = -tci
            benefit = 0.0
        else:
            investment = 0.0
            benefit = net_annual_benefit
        net = investment + benefit
        cumulative += net
        rows.append(CashFlowRow(
            year=year,
            investment=investment,
            benefit=benefit,
            net_cash_flow=net,
            cumulative=cumulative,
        ))
    return rows


def net_cash_flows(rows: List[CashFlowRow]) -> List[float]:
    return [r.net_cash_flow for r in rows]

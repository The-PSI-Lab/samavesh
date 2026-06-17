from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EconomicsResult:
    discount_rate: float
    npv: float
    irr: Optional[float]
    simple_payback_years: Optional[float]
    discounted_payback_years: Optional[float]


def npv_at_rate(rate, cash_flows: List[float]) -> float:
    return sum(cf / ((1 + rate) ** yr) for yr, cf in enumerate(cash_flows))


def _safe_irr(cash_flows: List[float]) -> Optional[float]:
    r = 0.1
    for _ in range(200):
        npv_r = sum(cf / ((1 + r) ** yr) for yr, cf in enumerate(cash_flows))
        dnpv = sum(-yr * cf / ((1 + r) ** (yr + 1)) for yr, cf in enumerate(cash_flows)) if r != -1 else 0
        if abs(dnpv) < 1e-12:
            return None
        r_new = r - npv_r / dnpv
        if abs(r_new - r) < 1e-7:
            return float(r_new)
        r = r_new
    return None


def _simple_payback(tci, net_annual_benefit) -> Optional[float]:
    if net_annual_benefit <= 0:
        return None
    return tci / net_annual_benefit


def _discounted_payback(cash_flows: List[float], rate) -> Optional[float]:
    cumulative = 0.0
    previous_cumulative = 0.0
    for year, cf in enumerate(cash_flows):
        discounted = cf / ((1.0 + rate) ** year)
        previous_cumulative = cumulative
        cumulative += discounted
        if year > 0 and cumulative >= 0:
            year_flow = discounted
            if year_flow == 0:
                return float(year)
            fraction = -previous_cumulative / year_flow
            return (year - 1) + fraction
    return None


def compute_economics(cash_flows: List[float],
                      tci,
                      net_annual_benefit,
                      discount_rate) -> EconomicsResult:
    discount_rate = float(discount_rate)
    tci = float(tci)
    net_annual_benefit = float(net_annual_benefit)

    return EconomicsResult(
        discount_rate=discount_rate,
        npv=npv_at_rate(discount_rate, cash_flows),
        irr=_safe_irr(cash_flows),
        simple_payback_years=_simple_payback(tci, net_annual_benefit),
        discounted_payback_years=_discounted_payback(cash_flows, discount_rate),
    )

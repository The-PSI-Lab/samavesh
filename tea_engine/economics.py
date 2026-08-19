"""
economics.py
============
Time-value-of-money measures, computed from the net cash flow list.

    NPV  : numpy_financial.npv(discount_rate, cash_flows)
           cash_flows[0] sits at year 0 and is NOT discounted (npf convention).
    IRR  : numpy_financial.irr(cash_flows). Undefined when there is no sign
           change or the solver fails -> returned as None.
    Simple Payback   : TCI / Net Annual Benefit. None if benefit <= 0.
    Discounted Payback : first year the discounted cumulative cash flow turns
           non-negative, linearly interpolated within the year. None if it
           never recovers inside the plant life.

Bad economics (net benefit <= 0) do not raise. They return None so the web
layer can print "N/A" instead of crashing or showing a misleading number.
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy_financial as npf


@dataclass
class EconomicsResult:
    discount_rate: float
    npv: float
    irr: Optional[float]
    simple_payback_years: Optional[float]
    discounted_payback_years: Optional[float]


def npv_at_rate(rate, cash_flows: List[float]) -> float:
    """NPV for an arbitrary rate. Used for the sensitivity sweeps too."""
    return float(npf.npv(rate, cash_flows))


def _safe_irr(cash_flows: List[float]) -> Optional[float]:
    try:
        value = npf.irr(cash_flows)
    except Exception:
        return None
    if value is None:
        return None
    # npf.irr returns nan when there is no real solution.
    if value != value:  # nan check without importing math
        return None
    return float(value)


def _simple_payback(tci, net_annual_benefit) -> Optional[float]:
    if net_annual_benefit <= 0:
        return None
    return tci / net_annual_benefit


def _discounted_payback(cash_flows: List[float], rate) -> Optional[float]:
    """Year at which discounted cumulative cash flow first reaches zero."""
    cumulative = 0.0
    previous_cumulative = 0.0
    for year, cf in enumerate(cash_flows):
        discounted = cf / ((1.0 + rate) ** year)
        previous_cumulative = cumulative
        cumulative += discounted
        if year > 0 and cumulative >= 0:
            # interpolate inside this year using the discounted flow
            year_flow = discounted
            if year_flow == 0:
                return float(year)
            fraction = -previous_cumulative / year_flow
            return (year - 1) + fraction
    return None  # never pays back within the analysed horizon


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

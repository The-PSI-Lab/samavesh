from dataclasses import dataclass


@dataclass
class OpexResult:
    heat_duty_kw: float
    operating_hours: float
    annual_energy_kwh: float
    utility_cost_per_kwh: float
    annual_savings: float
    maintenance_fraction: float
    maintenance_cost: float
    net_annual_benefit: float


def compute_opex(heat_duty_kw,
                 operating_hours,
                 utility_cost_per_kwh,
                 tci,
                 maintenance_fraction):
    heat_duty_kw = float(heat_duty_kw)
    operating_hours = float(operating_hours)
    utility_cost_per_kwh = float(utility_cost_per_kwh)
    tci = float(tci)
    maintenance_fraction = float(maintenance_fraction)

    annual_energy_kwh = heat_duty_kw * operating_hours
    annual_savings = annual_energy_kwh * utility_cost_per_kwh
    maintenance_cost = tci * maintenance_fraction
    net_annual_benefit = annual_savings - maintenance_cost

    return OpexResult(
        heat_duty_kw=heat_duty_kw,
        operating_hours=operating_hours,
        annual_energy_kwh=annual_energy_kwh,
        utility_cost_per_kwh=utility_cost_per_kwh,
        annual_savings=annual_savings,
        maintenance_fraction=maintenance_fraction,
        maintenance_cost=maintenance_cost,
        net_annual_benefit=net_annual_benefit,
    )

from dataclasses import dataclass


@dataclass
class CapexResult:
    purchase_cost: float
    bare_module_factor: float
    bare_module_cost: float
    contingency_fraction: float
    contingency_cost: float
    fci: float
    working_capital_fraction: float
    working_capital: float
    tci: float


def compute_capex(purchase_cost,
                  bare_module_factor,
                  contingency_fraction,
                  working_capital_fraction):
    purchase_cost = float(purchase_cost)
    bare_module_factor = float(bare_module_factor)
    contingency_fraction = float(contingency_fraction)
    working_capital_fraction = float(working_capital_fraction)

    bare_module_cost = purchase_cost * bare_module_factor
    contingency_cost = bare_module_cost * contingency_fraction
    fci = bare_module_cost + contingency_cost
    working_capital = fci * working_capital_fraction
    tci = fci + working_capital

    return CapexResult(
        purchase_cost=purchase_cost,
        bare_module_factor=bare_module_factor,
        bare_module_cost=bare_module_cost,
        contingency_fraction=contingency_fraction,
        contingency_cost=contingency_cost,
        fci=fci,
        working_capital_fraction=working_capital_fraction,
        working_capital=working_capital,
        tci=tci,
    )

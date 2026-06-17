from flask import Flask, render_template, request
from tea_engine import (
    units,
    compute_capex,
    compute_opex,
    build_cashflow,
    net_cash_flows,
    compute_economics,
    npv_at_rate,
)

app = Flask(__name__)

TEAM = [
    "Srikar Nemani",
    "Aaditya Chhiroulha",
    "V. S. Mohammad Aakhib",
    "Sangram Chakraborty",
    "Trishita Chandra",
]

CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "\u20ac", "GBP": "\u00a3",
    "INR": "\u20b9", "JPY": "\u00a5",
}


def _num(name, default=0.0):
    raw = request.form.get(name, "")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


def _int(name, default=0):
    try:
        return int(float(request.form.get(name, default)))
    except (TypeError, ValueError):
        return int(default)


def _pct(name, default=0.0):
    return _num(name, default) / 100.0


@app.route("/")
def landing():
    return render_template("index.html", team=TEAM)


@app.route("/equipment")
def equipment():
    return render_template("equipment.html")


@app.route("/analysis/<eq_type>")
def analysis(eq_type):
    return render_template("analysis.html", eq_type=eq_type)


@app.route("/calculate", methods=["POST"])
def calculate():
    # --- technical inputs ---------------------------------------------------
    heat_duty_w = units.to_watts(_num("heat_duty"), request.form.get("heat_duty_unit", "kW"))
    heat_duty_kw = units.watts_to_kw(heat_duty_w)
    area_m2 = units.to_m2(_num("area"), request.form.get("area_unit", "m2"))
    shell_id_m = units.to_metres(_num("shell_id"), request.form.get("shell_id_unit", "m"))
    tube_length_m = units.to_metres(_num("tube_length"), request.form.get("tube_length_unit", "m"))
    tube_od_m = units.to_metres(_num("tube_od"), request.form.get("tube_od_unit", "mm"))
    pressure_pa = units.to_pascal(_num("design_pressure"), request.form.get("pressure_unit", "bar"))
    temp_k = units.to_kelvin(_num("design_temp"), request.form.get("temp_unit", "degC"))
    num_tubes = _int("num_tubes")

    # --- economic inputs ----------------------------------------------------
    purchase_cost = _num("purchase_cost", 50000)
    bare_module_factor = _num("bare_module_factor", 3.291)
    contingency_fraction = _pct("contingency_pct", 18.0)
    working_capital_fraction = _pct("working_capital_pct", 15.0)
    maintenance_fraction = _pct("maintenance_pct", 5.0)
    plant_life = _int("plant_life", 15)
    discount_rate = _pct("discount_rate", 10.0)
    operating_hours = _num("operating_hours", 8000.0)
    utility_cost_per_kwh = units.utility_cost_to_per_kwh(
        _num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")
    )

    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")

    # --- engine -------------------------------------------------------------
    capex = compute_capex(
        purchase_cost, bare_module_factor,
        contingency_fraction, working_capital_fraction,
    )

    opex = compute_opex(
        heat_duty_kw, operating_hours, utility_cost_per_kwh,
        capex.tci, maintenance_fraction,
    )

    rows = build_cashflow(capex.tci, opex.net_annual_benefit, plant_life)
    flows = net_cash_flows(rows)
    econ = compute_economics(flows, capex.tci, opex.net_annual_benefit, discount_rate)

    # --- sensitivity sweeps -------------------------------------------------
    sensitivity = _build_sensitivity(
        capex=capex, opex=opex, plant_life=plant_life,
        discount_rate=discount_rate, purchase_cost=purchase_cost,
        bare_module_factor=bare_module_factor,
        contingency_fraction=contingency_fraction,
        working_capital_fraction=working_capital_fraction,
        maintenance_fraction=maintenance_fraction,
        annual_energy_kwh=opex.annual_energy_kwh,
        utility_cost_per_kwh=utility_cost_per_kwh,
    )

    # --- chart data payload -------------------------------------------------
    chart_data = {
        "currency": symbol,
        "capex_breakdown": {
            "labels": ["Purchase cost", "Installation", "Contingency", "Working capital"],
            "values": [
                capex.purchase_cost,
                capex.bare_module_cost - capex.purchase_cost,
                capex.contingency_cost,
                capex.working_capital,
            ],
        },
        "opex_breakdown": {
            "labels": ["Maintenance", "Net annual benefit"],
            "values": [opex.maintenance_cost, max(opex.net_annual_benefit, 0.0)],
        },
        "cashflow": {
            "years": [r.year for r in rows],
            "net": [r.net_cash_flow for r in rows],
            "cumulative": [r.cumulative for r in rows],
        },
        "npv_sensitivity": sensitivity["npv"],
        "discount_sensitivity": sensitivity["discount"],
        "irr": econ.irr,
    }

    return render_template(
        "results.html",
        symbol=symbol, currency=currency,
        team=TEAM,
        tag_id=request.form.get("tag_id", "N/A"),
        hx_type=request.form.get("hx_type", "Shell and Tube"),
        shell_material=request.form.get("shell_material", "Carbon Steel"),
        tube_material=request.form.get("tube_material", "Carbon Steel"),
        si={
            "heat_duty_kw": heat_duty_kw, "area_m2": area_m2,
            "shell_id_m": shell_id_m, "tube_length_m": tube_length_m,
            "tube_od_m": tube_od_m, "num_tubes": num_tubes,
            "pressure_pa": pressure_pa, "temp_k": temp_k,
        },
        capex=capex, opex=opex, econ=econ, rows=rows,
        plant_life=plant_life, chart_data=chart_data,
    )


def _build_sensitivity(capex, opex, plant_life, discount_rate,
                       purchase_cost, bare_module_factor,
                       contingency_fraction, working_capital_fraction,
                       maintenance_fraction, annual_energy_kwh,
                       utility_cost_per_kwh):
    pct_changes = list(range(-50, 51, 10))
    utility_line, purchase_line = [], []

    for pct in pct_changes:
        m = 1.0 + pct / 100.0

        savings = annual_energy_kwh * (utility_cost_per_kwh * m)
        net_benefit = savings - opex.maintenance_cost
        rows = build_cashflow(capex.tci, net_benefit, plant_life)
        utility_line.append(npv_at_rate(discount_rate, net_cash_flows(rows)))

        c = compute_capex(purchase_cost * m, bare_module_factor,
                          contingency_fraction, working_capital_fraction)
        net_benefit_p = opex.annual_savings - c.tci * maintenance_fraction
        rows_p = build_cashflow(c.tci, net_benefit_p, plant_life)
        purchase_line.append(npv_at_rate(discount_rate, net_cash_flows(rows_p)))

    base_flows = net_cash_flows(build_cashflow(capex.tci, opex.net_annual_benefit, plant_life))
    rate_axis = [r / 100.0 for r in range(0, 31, 2)]
    npv_curve = [npv_at_rate(r, base_flows) for r in rate_axis]

    return {
        "npv": {
            "pct_changes": pct_changes,
            "utility": utility_line,
            "purchase": purchase_line,
        },
        "discount": {
            "rates": [r * 100.0 for r in rate_axis],
            "npv": npv_curve,
        },
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)

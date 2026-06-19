from flask import Flask, render_template, request, session
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
app.secret_key = "samavesh-psi-lab-2026"

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


@app.route("/team")
def team():
    return render_template("team.html", team=TEAM)


@app.route("/plant-specs", methods=["GET", "POST"])
def plant_specs():
    if request.method == "POST":
        session["project_id"] = request.form.get("project_id", "")
        session["user_name"] = request.form.get("user_name", "")
        session["project_desc"] = request.form.get("project_desc", "")
        session["plant_capacity"] = request.form.get("plant_capacity", "")
        session["cepei"] = request.form.get("cepei", "")
        from flask import redirect, url_for
        return redirect(url_for("material_balance"))
    return render_template("plant_specs.html", saved=False)


@app.route("/material-balance", methods=["GET", "POST"])
def material_balance():
    if request.method == "POST":
        feed_names = request.form.getlist("feed_name[]")
        feed_costs = request.form.getlist("feed_cost[]")
        prod_names = request.form.getlist("prod_name[]")
        prod_costs = request.form.getlist("prod_cost[]")
        session["feedstocks"] = list(zip(feed_names, feed_costs))
        session["products"] = list(zip(prod_names, prod_costs))
        from flask import redirect, url_for
        return redirect(url_for("equipment"))
    return render_template("material_balance.html",
                           feedstocks=[], products=[])


@app.route("/equipment")
def equipment():
    return render_template("equipment.html",
                           project_id=session.get("project_id", ""))


@app.route("/analysis/<eq_type>")
def analysis(eq_type):
    template_map = {
        "distillation_column": "analysis_distillation.html",
        "pump": "analysis_pump.html",
        "vessel": "analysis_vessel.html",
        "reactor": "analysis_reactor.html",
        "compressor": "analysis_compressor.html",
        "valve": "analysis_valve.html",
        "kod": "analysis_kod.html",
        "dryer": "analysis_dryer.html",
        "adsorber": "analysis_adsorber.html",
        "absorber": "analysis_absorber.html",
        "cooler": "analysis_cooler.html",
        "blower": "analysis_blower.html",
        "fan": "analysis_fan.html",
        "heater": "analysis_heater.html",
        "plate": "analysis_plate.html",
        "thickener": "analysis_thickener.html",
        "clarifier": "analysis_clarifier.html",
        "filter": "analysis_filter.html",
        "centrifuge": "analysis_centrifuge.html",
        "mill": "analysis_mill.html",
    }
    tmpl = template_map.get(eq_type, "analysis.html")
    return render_template(tmpl, eq_type=eq_type)


@app.route("/calculate-purchase", methods=["POST"])
def calculate_purchase():
    bm = _num("bare_module_factor", 3.291)
    pc = _num("purchase_cost_manual", 50000)
    result = pc * bm
    return {"purchase_cost": pc, "bare_module_cost": result,
            "message": f"Purchase: ${pc:,.0f} \u00d7 {bm:.3f} = ${result:,.0f}"}


@app.route("/calculate", methods=["POST"])
def calculate():
    heat_duty_w = units.to_watts(_num("heat_duty"), request.form.get("heat_duty_unit", "kW"))
    heat_duty_kw = units.watts_to_kw(heat_duty_w)
    area_m2 = units.to_m2(_num("area"), request.form.get("area_unit", "m2"))
    shell_id_m = units.to_metres(_num("shell_id"), request.form.get("shell_id_unit", "m"))
    tube_length_m = units.to_metres(_num("tube_length"), request.form.get("tube_length_unit", "m"))
    tube_od_m = units.to_metres(_num("tube_od"), request.form.get("tube_od_unit", "mm"))
    pressure_pa = units.to_pascal(_num("design_pressure"), request.form.get("pressure_unit", "bar"))
    temp_k = units.to_kelvin(_num("design_temp"), request.form.get("temp_unit", "degC"))
    num_tubes = _int("num_tubes")

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
        project_id=session.get("project_id", ""),
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


def _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, contingency_fraction, working_capital_fraction, maintenance_fraction, plant_life, discount_rate, operating_hours, utility_cost_per_kwh, currency, symbol, hx_type, shell_material, tube_material, si_dict):
    capex = compute_capex(purchase_cost, bare_module_factor, contingency_fraction, working_capital_fraction)
    opex = compute_opex(heat_duty_kw, operating_hours, utility_cost_per_kwh, capex.tci, maintenance_fraction)
    rows = build_cashflow(capex.tci, opex.net_annual_benefit, plant_life)
    flows = net_cash_flows(rows)
    econ = compute_economics(flows, capex.tci, opex.net_annual_benefit, discount_rate)
    sensitivity = _build_sensitivity(capex, opex, plant_life, discount_rate, purchase_cost, bare_module_factor, contingency_fraction, working_capital_fraction, maintenance_fraction, opex.annual_energy_kwh, utility_cost_per_kwh)
    chart_data = {
        "currency": symbol,
        "capex_breakdown": {"labels": ["Purchase cost", "Installation", "Contingency", "Working capital"], "values": [capex.purchase_cost, capex.bare_module_cost - capex.purchase_cost, capex.contingency_cost, capex.working_capital]},
        "opex_breakdown": {"labels": ["Maintenance", "Net annual benefit"], "values": [opex.maintenance_cost, max(opex.net_annual_benefit, 0.0)]},
        "cashflow": {"years": [r.year for r in rows], "net": [r.net_cash_flow for r in rows], "cumulative": [r.cumulative for r in rows]},
        "npv_sensitivity": sensitivity["npv"],
        "discount_sensitivity": sensitivity["discount"],
        "irr": econ.irr,
    }
    return render_template("results.html", symbol=symbol, currency=currency, team=TEAM, project_id=session.get("project_id", ""), tag_id=request.form.get("tag_id", "N/A"), hx_type=hx_type, shell_material=shell_material, tube_material=tube_material, si=si_dict, capex=capex, opex=opex, econ=econ, rows=rows, plant_life=plant_life, chart_data=chart_data)


@app.route("/calculate-distillation", methods=["POST"])
def calculate_distillation():
    reboiler_kw = units.watts_to_kw(units.to_watts(_num("reboiler_duty"), request.form.get("reboiler_duty_unit", "kW")))
    condenser_kw = units.watts_to_kw(units.to_watts(_num("condenser_duty"), request.form.get("condenser_duty_unit", "kW")))
    heat_duty_kw = reboiler_kw + condenser_kw
    column_diameter_m = units.to_metres(_num("column_diameter"), request.form.get("column_diameter_unit", "m"))
    column_height_m = units.to_metres(_num("column_height"), request.form.get("column_height_unit", "m"))
    num_stages = _int("num_stages")
    pressure_pa = units.to_pascal(_num("operating_pressure"), request.form.get("pressure_unit", "bar"))
    temp_k = units.to_kelvin(_num("operating_temp"), request.form.get("temp_unit", "degC"))
    purchase_cost = _num("purchase_cost", 100000)
    bare_module_factor = _num("bare_module_factor", 4.0)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Distillation Column", request.form.get("column_material", "Carbon Steel"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": 0, "shell_id_m": column_diameter_m, "tube_length_m": column_height_m, "tube_od_m": 0, "num_tubes": num_stages, "pressure_pa": pressure_pa, "temp_k": temp_k})


@app.route("/calculate-pump", methods=["POST"])
def calculate_pump():
    power_kw = _num("power")
    if request.form.get("power_unit") == "hp":
        power_kw *= 0.7457
    heat_duty_kw = power_kw
    purchase_cost = _num("purchase_cost", 25000)
    bare_module_factor = _num("bare_module_factor", 3.0)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Pump", request.form.get("pump_material", "Carbon Steel"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-vessel", methods=["POST"])
def calculate_vessel():
    heat_duty_kw = _num("heat_duty", 0)
    purchase_cost = _num("purchase_cost", 50000)
    bare_module_factor = _num("bare_module_factor", 3.0)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Pressure Vessel", request.form.get("vessel_material", "Carbon Steel"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-reactor", methods=["POST"])
def calculate_reactor():
    heat_duty_kw = units.watts_to_kw(units.to_watts(_num("heat_duty"), request.form.get("heat_duty_unit", "kW")))
    purchase_cost = _num("purchase_cost", 150000)
    bare_module_factor = _num("bare_module_factor", 4.0)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Reactor", request.form.get("reactor_material", "Carbon Steel"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-compressor", methods=["POST"])
def calculate_compressor():
    power_kw = _num("power")
    if request.form.get("power_unit") == "hp":
        power_kw *= 0.7457
    heat_duty_kw = power_kw
    purchase_cost = _num("purchase_cost", 80000)
    bare_module_factor = _num("bare_module_factor", 3.5)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Compressor", request.form.get("compressor_material", "Carbon Steel"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-valve", methods=["POST"])
def calculate_valve():
    heat_duty_kw = 0
    purchase_cost = _num("purchase_cost", 5000)
    bare_module_factor = _num("bare_module_factor", 2.5)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Valve", request.form.get("valve_material", "Carbon Steel"), "N/A", {"heat_duty_kw": 0, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-kod", methods=["POST"])
def calculate_kod():
    heat_duty_kw = 0
    purchase_cost = _num("purchase_cost", 30000)
    bare_module_factor = _num("bare_module_factor", 3.0)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Knock Out Drum", request.form.get("vessel_material", "Carbon Steel"), "N/A", {"heat_duty_kw": 0, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-dryer", methods=["POST"])
def calculate_dryer():
    heat_duty_kw = units.watts_to_kw(units.to_watts(_num("heat_duty"), request.form.get("heat_duty_unit", "kW")))
    purchase_cost = _num("purchase_cost", 60000)
    bare_module_factor = _num("bare_module_factor", 3.5)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Dryer", request.form.get("dryer_material", "Carbon Steel"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-adsorber", methods=["POST"])
def calculate_adsorber():
    heat_duty_kw = 0
    purchase_cost = _num("purchase_cost", 60000)
    bare_module_factor = _num("bare_module_factor", 3.2)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Adsorber", request.form.get("adsorber_material", "Carbon Steel"), "N/A", {"heat_duty_kw": 0, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-absorber", methods=["POST"])
def calculate_absorber():
    heat_duty_kw = 0
    purchase_cost = _num("purchase_cost", 80000)
    bare_module_factor = _num("bare_module_factor", 3.5)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Absorber", request.form.get("absorber_material", "Carbon Steel"), "N/A", {"heat_duty_kw": 0, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-cooler", methods=["POST"])
def calculate_cooler():
    heat_duty_kw = units.watts_to_kw(units.to_watts(_num("heat_duty"), request.form.get("heat_duty_unit", "kW")))
    purchase_cost = _num("purchase_cost", 40000)
    bare_module_factor = _num("bare_module_factor", 3.0)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Cooler", request.form.get("cooler_material", "Carbon Steel"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": _num("area"), "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-blower", methods=["POST"])
def calculate_blower():
    power_kw = _num("power")
    if request.form.get("power_unit") == "hp":
        power_kw *= 0.7457
    heat_duty_kw = power_kw
    purchase_cost = _num("purchase_cost", 35000)
    bare_module_factor = _num("bare_module_factor", 2.8)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Blower", request.form.get("blower_material", "Carbon Steel"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-fan", methods=["POST"])
def calculate_fan():
    power_kw = _num("power")
    if request.form.get("power_unit") == "hp":
        power_kw *= 0.7457
    heat_duty_kw = power_kw
    purchase_cost = _num("purchase_cost", 15000)
    bare_module_factor = _num("bare_module_factor", 2.5)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Fan", request.form.get("fan_material", "Carbon Steel"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-heater", methods=["POST"])
def calculate_heater():
    heat_duty_kw = units.watts_to_kw(units.to_watts(_num("heat_duty"), request.form.get("heat_duty_unit", "kW")))
    purchase_cost = _num("purchase_cost", 45000)
    bare_module_factor = _num("bare_module_factor", 3.0)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Heater", request.form.get("heater_material", "Carbon Steel"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": _num("area"), "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-plate", methods=["POST"])
def calculate_plate():
    heat_duty_kw = units.watts_to_kw(units.to_watts(_num("heat_duty"), request.form.get("heat_duty_unit", "kW")))
    purchase_cost = _num("purchase_cost", 30000)
    bare_module_factor = _num("bare_module_factor", 3.0)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Plate HX", request.form.get("plate_material", "SS304"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": _num("plate_area"), "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-thickener", methods=["POST"])
def calculate_thickener():
    heat_duty_kw = 0
    purchase_cost = _num("purchase_cost", 50000)
    bare_module_factor = _num("bare_module_factor", 2.8)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Thickener", request.form.get("thickener_material", "Carbon Steel"), "N/A", {"heat_duty_kw": 0, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-clarifier", methods=["POST"])
def calculate_clarifier():
    heat_duty_kw = 0
    purchase_cost = _num("purchase_cost", 55000)
    bare_module_factor = _num("bare_module_factor", 2.8)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Clarifier", request.form.get("clarifier_material", "Carbon Steel"), "N/A", {"heat_duty_kw": 0, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-filter", methods=["POST"])
def calculate_filter():
    heat_duty_kw = 0
    purchase_cost = _num("purchase_cost", 35000)
    bare_module_factor = _num("bare_module_factor", 2.5)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Filter", request.form.get("filter_material", "Carbon Steel"), "N/A", {"heat_duty_kw": 0, "area_m2": _num("filter_area"), "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-centrifuge", methods=["POST"])
def calculate_centrifuge():
    power_kw = _num("power")
    if request.form.get("power_unit") == "hp":
        power_kw *= 0.7457
    heat_duty_kw = power_kw
    purchase_cost = _num("purchase_cost", 60000)
    bare_module_factor = _num("bare_module_factor", 3.0)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Centrifuge", request.form.get("centrifuge_material", "SS304"), "N/A", {"heat_duty_kw": heat_duty_kw, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/calculate-mill", methods=["POST"])
def calculate_mill():
    power_kw = _num("power")
    if request.form.get("power_unit") == "hp":
        power_kw *= 0.7457
    heat_duty_kw = power_kw
    purchase_cost = _num("purchase_cost", 75000)
    bare_module_factor = _num("bare_module_factor", 3.5)
    currency = request.form.get("currency", "USD")
    symbol = CURRENCY_SYMBOLS.get(currency, "$")
    return _run_tea(heat_duty_kw, purchase_cost, bare_module_factor, _pct("contingency_pct", 18.0), _pct("working_capital_pct", 15.0), _pct("maintenance_pct", 5.0), _int("plant_life", 15), _pct("discount_rate", 10.0), _num("operating_hours", 8000.0), units.utility_cost_to_per_kwh(_num("utility_cost"), request.form.get("utility_cost_unit", "$/kWh")), currency, symbol, "Mill", request.form.get("lining_material", "Carbon Steel"), request.form.get("mill_type", "Ball Mill"), {"heat_duty_kw": heat_duty_kw, "area_m2": 0, "shell_id_m": 0, "tube_length_m": 0, "tube_od_m": 0, "num_tubes": 0, "pressure_pa": 0, "temp_k": 0})


@app.route("/net-capex")
def net_capex():
    return render_template("net_capex.html")


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

POWER_TO_W = {
    "W": 1.0,
    "kW": 1.0e3,
    "MW": 1.0e6,
    "hp": 745.699872,
    "Btu/hr": 0.29307107,
}

AREA_TO_M2 = {
    "m2": 1.0,
    "m²": 1.0,
    "ft2": 0.09290304,
    "ft²": 0.09290304,
}

PRESSURE_TO_PA = {
    "Pa": 1.0,
    "kPa": 1.0e3,
    "MPa": 1.0e6,
    "bar": 1.0e5,
    "barg": 1.0e5,
    "psi": 6894.757293168,
    "psia": 6894.757293168,
    "psig": 6894.757293168,
    "torr": 133.322368,
    "mmWG": 9.80665,
}

LENGTH_TO_M = {
    "mm": 1.0e-3,
    "cm": 1.0e-2,
    "m": 1.0,
    "in": 0.0254,
    "ft": 0.3048,
}

UTILITY_COST_TO_PER_KWH = {
    "$/kWh": 1.0,
    "$/MWh": 1.0 / 1000.0,
    "$/GJ": 0.0036,
    "$/lb steam": 3.41,
    "$/lb_steam": 3.41,
    "$/gal": 6.0,
    "$/lb": 1.5,
    "$/kg": 3.3,
}

FLOW_RATE_TO_M3_S = {
    "m3/h": 1.0 / 3600.0,
    "L/min": 1.0 / 60000.0,
    "gal/min": 0.00378541 / 60.0,
    "kg/h": 1.0 / 3600.0,
    "lb/h": 0.453592 / 3600.0,
}


def to_watts(value, unit):
    return float(value) * POWER_TO_W[unit]


def to_m2(value, unit):
    return float(value) * AREA_TO_M2[unit]


def to_pascal(value, unit):
    return float(value) * PRESSURE_TO_PA[unit]


def to_metres(value, unit):
    return float(value) * LENGTH_TO_M[unit]


def utility_cost_to_per_kwh(value, unit):
    return float(value) * UTILITY_COST_TO_PER_KWH[unit]


def flow_rate_to_m3_s(value, unit):
    return float(value) * FLOW_RATE_TO_M3_S[unit]


def to_kelvin(value, unit):
    value = float(value)
    # Normalize unit: remove degree symbol, spaces, entity codes
    unit = unit.replace("&deg;", "").replace("°", "").strip()
    if unit in ("K", "Kelvin"):
        return value
    if unit in ("R", "Rankine"):
        return value * 5.0 / 9.0
    if unit in ("C", "degC", "Celsius"):
        return value + 273.15
    if unit in ("F", "degF", "Fahrenheit"):
        return (value - 32.0) * 5.0 / 9.0 + 273.15
    raise ValueError(f"Unknown temperature unit: {unit}")


def watts_to_kw(power_w):
    return power_w / 1000.0

POWER_TO_W = {
    "W": 1.0,
    "kW": 1.0e3,
    "MW": 1.0e6,
}

AREA_TO_M2 = {
    "m2": 1.0,
    "ft2": 0.09290304,
}

PRESSURE_TO_PA = {
    "Pa": 1.0,
    "kPa": 1.0e3,
    "MPa": 1.0e6,
    "bar": 1.0e5,
    "psi": 6894.757293168,
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


def to_kelvin(value, unit):
    value = float(value)
    if unit == "K":
        return value
    if unit == "degC":
        return value + 273.15
    if unit == "degF":
        return (value - 32.0) * 5.0 / 9.0 + 273.15
    raise ValueError(f"Unknown temperature unit: {unit}")


def watts_to_kw(power_w):
    return power_w / 1000.0

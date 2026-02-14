"""
PLDM Table 75 -> UCUM mapping

this module converts PLDM sensor or effector reading units to UCUM (Unified Code for 
Units of Measure) strings for use with Redfish schema.
"""

PLDM_SENSOR_UNITS = [
    {"code": 0,   "name": "None",                "numerators": [],        "denominators": [], "modifier": 0},
    {"code": 1,   "name": "Unspecified",         "numerators": [],        "denominators": [], "modifier": 0},
    {"code": 2,   "name": "Degrees C",           "numerators": ["Cel"],   "denominators": [], "modifier": 0},
    {"code": 3,   "name": "Degrees F",           "numerators": ["degF"],  "denominators": [], "modifier": 0},
    {"code": 4,   "name": "Kelvins",             "numerators": ["K"],     "denominators": [], "modifier": 0},
    {"code": 5,   "name": "Volts",               "numerators": ["V"],     "denominators": [], "modifier": 0},
    {"code": 6,   "name": "Amps",                "numerators": ["A"],     "denominators": [], "modifier": 0},
    {"code": 7,   "name": "Watts",               "numerators": ["W"],     "denominators": [], "modifier": 0},
    {"code": 8,   "name": "Joules",              "numerators": ["J"],     "denominators": [], "modifier": 0},
    {"code": 9,   "name": "Coulombs",            "numerators": ["C"],     "denominators": [], "modifier": 0},
    {"code": 10,  "name": "VA",                  "numerators": ["VA"],    "denominators": [], "modifier": 0},
    {"code": 11,  "name": "Nits",                "numerators": [],        "denominators": [], "modifier": 0},
    {"code": 12,  "name": "Lumens",              "numerators": ["lm"],    "denominators": [], "modifier": 0},
    {"code": 13,  "name": "Lux",                 "numerators": ["lx"],    "denominators": [], "modifier": 0},
    {"code": 14,  "name": "Candelas",            "numerators": ["cd"],    "denominators": [], "modifier": 0},
    {"code": 15,  "name": "kPa",                 "numerators": ["Pa"],    "denominators": [], "modifier": 3},
    {"code": 16,  "name": "PSI",                 "numerators": ["psi"],   "denominators": [], "modifier": 0},
    {"code": 17,  "name": "Newtons",             "numerators": ["N"],     "denominators": [], "modifier": 0},
    {"code": 18,  "name": "CFM",                 "numerators": [],        "denominators": [], "modifier": 0},
    {"code": 19,  "name": "RPM",                 "numerators": ["rev"],   "denominators": ["min"], "modifier": 0},
    {"code": 20,  "name": "Hertz",               "numerators": ["Hz"],    "denominators": [], "modifier": 0},
    {"code": 21,  "name": "Seconds",             "numerators": ["s"],     "denominators": [], "modifier": 0},
    {"code": 22,  "name": "Minutes",             "numerators": ["min"],   "denominators": [], "modifier": 0},
    {"code": 23,  "name": "Hours",               "numerators": ["h"],     "denominators": [], "modifier": 0},
    {"code": 24,  "name": "Days",                "numerators": ["d"],     "denominators": [], "modifier": 0},
    {"code": 25,  "name": "Weeks",               "numerators": ["wk"],    "denominators": [], "modifier": 0},
    {"code": 26,  "name": "Mils",                "numerators": ["mil"],   "denominators": [], "modifier": 0},
    {"code": 27,  "name": "Inches",              "numerators": ["in"],    "denominators": [], "modifier": 0},
    {"code": 28,  "name": "Feet",                "numerators": ["ft"],    "denominators": [], "modifier": 0},
    {"code": 29,  "name": "Cubic Inches",        "numerators": ["in","in","in"],    "denominators": [], "modifier": 0},
    {"code": 30,  "name": "Cubic Feet",          "numerators": ["ft","ft","ft"],    "denominators": [], "modifier": 0},
    {"code": 31,  "name": "Meters",              "numerators": ["m"],     "denominators": [], "modifier": 0},
    {"code": 32,  "name": "Cubic Centimeters",   "numerators": ["cm","cm","cm"],    "denominators": [], "modifier": 0},
    {"code": 33,  "name": "Cubic Meters",        "numerators": ["m","m","m"],     "denominators": [], "modifier": 0},
    {"code": 34,  "name": "Liters",              "numerators": ["L"],     "denominators": [], "modifier": 0},
    {"code": 35,  "name": "Fluid Ounces",        "numerators": ["floz"],  "denominators": [], "modifier": 0},
    {"code": 36,  "name": "Radians",             "numerators": ["rad"],   "denominators": [], "modifier": 0},
    {"code": 37,  "name": "Steradians",          "numerators": ["sr"],    "denominators": [], "modifier": 0},
    {"code": 38,  "name": "Revolutions",         "numerators": ["rev"],   "denominators": [], "modifier": 0},
    {"code": 39,  "name": "Cycles",              "numerators": ["cycle"], "denominators": [], "modifier": 0},
    {"code": 40,  "name": "Gravities",           "numerators": ["g"],     "denominators": [], "modifier": 0},
    {"code": 41,  "name": "Ounces",              "numerators": ["oz"],    "denominators": [], "modifier": 0},
    {"code": 42,  "name": "Pounds",              "numerators": ["lb"],    "denominators": [], "modifier": 0},
    {"code": 43,  "name": "Foot-Pounds",         "numerators": ["ft","lb"], "denominators": [], "modifier": 0},
    {"code": 44,  "name": "Ounce-Inches",        "numerators": ["oz","in"], "denominators": [], "modifier": 0},
    {"code": 45,  "name": "Gauss",               "numerators": ["G"],     "denominators": [], "modifier": 0},
    {"code": 46,  "name": "Gilberts",            "numerators": ["Gb"],    "denominators": [], "modifier": 0},
    {"code": 47,  "name": "Henries",             "numerators": ["H"],     "denominators": [], "modifier": 0},
    {"code": 48,  "name": "Farads",              "numerators": ["F"],     "denominators": [], "modifier": 0},
    {"code": 49,  "name": "Ohms",                "numerators": ["Ohm"],   "denominators": [], "modifier": 0},
    {"code": 50,  "name": "Siemens",             "numerators": ["S"],     "denominators": [], "modifier": 0},
    {"code": 51,  "name": "Moles",               "numerators": ["mol"],   "denominators": [], "modifier": 0},
    {"code": 52,  "name": "Becquerels",          "numerators": ["Bq"],    "denominators": [], "modifier": 0},
    {"code": 53,  "name": "PPM (parts/million)", "numerators": ["ppm"],   "denominators": [], "modifier": 0},
    {"code": 54,  "name": "Decibels",            "numerators": ["dB"],    "denominators": [], "modifier": 0},
    {"code": 55,  "name": "DbA",                 "numerators": ["dB(A)"], "denominators": [], "modifier": 0},
    {"code": 56,  "name": "DbC",                 "numerators": ["dB(C)"], "denominators": [], "modifier": 0},
    {"code": 57,  "name": "Grays",               "numerators": ["Gy"],    "denominators": [], "modifier": 0},
    {"code": 58,  "name": "Sieverts",            "numerators": ["Sv"],    "denominators": [], "modifier": 0},
    {"code": 59,  "name": "Color Temperature Degrees K", "numerators": ["K"], "denominators": [], "modifier": 0},
    {"code": 60,  "name": "Bits",                "numerators": ["bit"],   "denominators": [], "modifier": 0},
    {"code": 61,  "name": "Bytes",               "numerators": ["By"],    "denominators": [], "modifier": 0},
    {"code": 62,  "name": "Words (data)",        "numerators": [],        "denominators": [], "modifier": 0},
    {"code": 63,  "name": "DoubleWords",         "numerators": [],        "denominators": [], "modifier": 0},
    {"code": 64,  "name": "QuadWords",           "numerators": [],        "denominators": [], "modifier": 0},
    {"code": 65,  "name": "Percentage",          "numerators": ["%"],     "denominators": [], "modifier": 0},
    {"code": 66,  "name": "Pascals",             "numerators": ["Pa"],    "denominators": [], "modifier": 0},
    {"code": 67,  "name": "Counts",              "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 68,  "name": "Grams",               "numerators": ["g"],     "denominators": [], "modifier": 0},
    {"code": 69,  "name": "Newton-meters",       "numerators": ["N","m"],   "denominators": [], "modifier": 0},
    {"code": 70,  "name": "Hits",                "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 71,  "name": "Misses",              "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 72,  "name": "Retries",             "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 73,  "name": "Overruns/Overflows",  "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 74,  "name": "Underruns",           "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 75,  "name": "Collisions",          "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 76,  "name": "Packets",             "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 77,  "name": "Messages",            "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 78,  "name": "Characters",          "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 79,  "name": "Errors",              "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 80,  "name": "Corrected Errors",    "numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 81,  "name": "Uncorrectable Errors","numerators": [""],      "denominators": [], "modifier": 0},
    {"code": 82,  "name": "Square Mils",         "numerators": ["mil","mil"], "denominators": [], "modifier": 0},
    {"code": 83,  "name": "Square Inches",       "numerators": ["in","in"],   "denominators": [], "modifier": 0},
    {"code": 84,  "name": "Square Feet",         "numerators": ["ft","ft"],   "denominators": [], "modifier": 0},
    {"code": 85,  "name": "Square Centimeters",  "numerators": ["cm","cm"],   "denominators": [], "modifier": 0},
    {"code": 86,  "name": "Square Meters",       "numerators": ["m","m"],     "denominators": [], "modifier": 0},
    {"code": 255, "name": "OEMUnit",             "numerators": [],    "denominators": [], "modifier": 0},
]

PLDM_RATE_UNITS = [
    {"code": 0,   "name": "None",                "numerators": [],        "denominators": [], "modifier": 0},
    {"code": 1,   "name": "Per MicroSecond",         "numerators": [],        "denominators": ['s'], "modifier": 6},
    {"code": 2,   "name": "Per MilliSecond",           "numerators": [],   "denominators": ['s'], "modifier": 3},
    {"code": 3,   "name": "Per Second",           "numerators": [],  "denominators": ['s'], "modifier": 0},
    {"code": 4,   "name": "Per Minute",             "numerators": [],     "denominators": ['min'], "modifier": 0},
    {"code": 5,   "name": "Per Hour",               "numerators": [],     "denominators": ['h'], "modifier": 0},
    {"code": 6,   "name": "Per Day",                "numerators": [],     "denominators": ['d'], "modifier": 0},
    {"code": 7,   "name": "Per Week",               "numerators": [],     "denominators": ['wk'], "modifier": 0},
    {"code": 8,   "name": "Per Month",              "numerators": [],     "denominators": ['mo'], "modifier": 0},
    {"code": 9,   "name": "Per Year",            "numerators": [],     "denominators": ['a'], "modifier": 0},
]

from collections import Counter

Power_Modifier_String = [
    {"str": "Y", "power":24},
    {"str": "Z", "power":21},
    {"str": "E", "power":18},
    {"str": "P", "power":15},
    {"str": "T", "power":12},
    {"str": "G", "power":9},
    {"str": "M", "power":6},
    {"str": "k", "power":3},
    {"str": "h", "power":2},
    {"str": "da", "power":1},
    {"str": "d", "power":-1},
    {"str": "c", "power":-2},
    {"str": "m", "power":-3},
    {"str": "u", "power":-6},
    {"str": "n", "power":-9},
    {"str": "p", "power":-12},
    {"str": "f", "power":-15},
    {"str": "a", "power":-18},
    {"str": "z", "power":-21},
    {"str": "y", "power":-24},
]

def pldm_unit_to_ucum(unit_code):
    """
    Convert a PLDM unit code to a UCUM string tuple.

    Args:
        unit_code (int): The PLDM unit code to convert.

    Returns:
        numerators, denominators, modifier
    """
    for unit in PLDM_SENSOR_UNITS:
        if unit["code"] == unit_code:
            return unit["numerators"], unit["denominators"], unit["modifier"]
    return None, None, None

def pldm_rate_to_ucum(unit_code):
    """
    Convert a PLDM rate code to a UCUM string tuple.

    Args:
        unit_code (int): The PLDM rate code to convert.

    Returns:
        numerators, denominators, modifier
    """
    for unit in PLDM_RATE_UNITS:
        if unit["code"] == unit_code:
            return unit["numerators"], unit["denominators"], unit["modifier"]
    return None, None, None

def pldm_divide(numerators, denominators):
    """
    Divide PLDM unit codes to get a combined UCUM string.

    Args:
        unit_code (int): The PLDM unit code to convert.

    Returns:
        numerators, denominators, modifier
    """
    # Use counters to safely subtract common elements without mutating while iterating
    num_cnt = Counter(numerators)
    den_cnt = Counter(denominators)
    # subtract intersection
    for key in list((num_cnt & den_cnt).elements()):
        # remove one occurrence from both
        num_cnt.subtract([key])
        den_cnt.subtract([key])

    # rebuild lists preserving multiplicity
    new_numerators = []
    for k, v in num_cnt.items():
        if v > 0:
            new_numerators.extend([k] * v)
    new_denominators = []
    for k, v in den_cnt.items():
        if v > 0:
            new_denominators.extend([k] * v)
    return new_numerators, new_denominators

def pldm_multiply_combine(strings):
    """
    Combine PLDM unit codes by multiplication to get a combined UCUM string.

    Args:
        strings (list): List of PLDM unit strings to combine.

    Returns:
        str: The resulting UCUM string.
    """
    # Return an empty string for empty input
    if not strings:
        return ""

    cnt = Counter(strings)
    # sort keys for deterministic output
    parts = []
    for key in sorted(cnt.keys()):
        if key == "":
            continue
        count = cnt[key]
        if count > 1:
            parts.append(f"{key}{count}")
        else:
            parts.append(key)
    return ".".join(parts)

def get_power_modifier_string(power_of_10):
    """
    Get the power modifier string for a given modifier power.

    Args:
        power_of_10 (int): The power modifier to convert.
    Returns:
        str: The corresponding power modifier string.
    """
    for modifier in Power_Modifier_String:
        if modifier["power"] == power_of_10:
            return modifier["str"]
    # if exact modifier not found, return empty string (no prefix)
    return ""


def pldm_unit_to_ucum_string(numerators, denominators, modifier_power):
    """
    Convert PLDM unit components to a UCUM string.

    Args:
        numerators (list): List of numerator unit strings.
        denominators (list): List of denominator unit strings.
        modifier_power(int): The power modifier for the units.

    Returns:
        str: The combined UCUM string.
    """
    numerators, denominators = pldm_divide(list(numerators), list(denominators))

    numerator_string = pldm_multiply_combine(numerators)
    denominator_string = pldm_multiply_combine(denominators)

    if denominator_string:
        if numerator_string:
            modifier_string = get_power_modifier_string(modifier_power)
            return f"{modifier_string}{numerator_string}/{denominator_string}"
        else:
            modifier_string = get_power_modifier_string(-modifier_power)
            return f"1/{modifier_string}{denominator_string}"
    else:
        modifier_string = get_power_modifier_string(modifier_power)
        return f"{modifier_string}{numerator_string}"

def pdr_units_to_ucum(base, base_power, aux, aux_power, rel, rate, aux_rate):
    """
    Convert PLDM unit codes to a UCUM string.

    Args:
        base (int): The base PLDM unit code.
        base_power (int): The power of the base unit.
        aux (int): The auxiliary PLDM unit code.
        aux_power (int): The power of the auxiliary unit.
        rel (int): The relationship between the base and auxiliary units (0 for multiplication, 1 for division).
        rate (int): The rate at which the units are changing (0 for per second, 1 for per minute, 2 for per hour).
        aux_rate (int): The rate at which the auxiliary units are changing (0 for per second, 1 for per minute, 2 for per hour).
    Returns:
        str: The corresponding UCUM string.
    """
    numerators = []
    denominators = []
    modifier_power = 0
    if base != 0:
        base_numerators, base_denominators, base_modifier = pldm_unit_to_ucum(base)
        if base_numerators is None:
            return ""
        numerators.extend(base_numerators)
        denominators.extend(base_denominators)
        modifier_power += base_modifier + base_power
    if aux != 0:
        aux_numerators, aux_denominators, aux_modifier = pldm_unit_to_ucum(aux)
        if aux_numerators is None:
            return ""
        if rel == 1:
            numerators.extend(aux_numerators)
            denominators.extend(aux_denominators)
            modifier_power += aux_modifier + aux_power
        elif rel == 0:
            numerators.extend(aux_denominators)
            denominators.extend(aux_numerators)
            modifier_power -= (aux_modifier + aux_power)
    if rate != 0:
        rate_numerators, rate_denominators, rate_modifier = pldm_rate_to_ucum(rate)
        numerators.extend(rate_numerators)
        denominators.extend(rate_denominators)
        modifier_power -= rate_modifier
    if aux_rate != 0:
        aux_rate_numerators, aux_rate_denominators, aux_rate_modifier = pldm_rate_to_ucum(aux_rate)
        numerators.extend(aux_rate_numerators)
        denominators.extend(aux_rate_denominators)
        modifier_power -= aux_rate_modifier

    return pldm_unit_to_ucum_string(numerators, denominators, modifier_power)


def pdr_units_to_ucum_string(base, base_power, aux, aux_power, rel, rate, aux_rate):
    """Alias that returns the UCUM string for PLDM PDR unit components.

    Kept for API compatibility: callers that expect `pdr_units_to_ucum_string`
    can call this function directly; it forwards to `pdr_units_to_ucum`.
    """
    return pdr_units_to_ucum(base, base_power, aux, aux_power, rel, rate, aux_rate)

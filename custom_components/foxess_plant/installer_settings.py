"""Installer settings the Fox app doesn't show, read from foxess_modbus (never written).

Grid standard codes are the FoxESS Modbus protocol's table 4-2 (V1.05.03.00); the inverter stores the number.
"""

from __future__ import annotations

from typing import Any

from .const import INSTALLER_ENTITY_SUFFIXES

GRID_STANDARDS: dict[int, tuple[str, str]] = {
    0: ("AS4777_AU", "Australia"),
    1: ("AS4777_NZ", "New Zealand"),
    2: ("G98_UK", "UK"),
    3: ("G99_UK", "UK"),
    4: ("EN50549_NL", "Netherlands"),
    5: ("CEI021_A", "Italy"),
    6: ("VDE0126", "Germany"),
    7: ("VDE4105_DE", "Germany"),
    8: ("NBR-220_BR", "Brazil"),
    9: ("NBR-240_BR", "Brazil"),
    10: ("IEC61727", "India"),
    11: ("Philippines", "Philippines"),
    12: ("NRS_SA", "South Africa"),
    13: ("Vietnam", "Vietnam"),
    14: ("EN50549_PL", "Poland"),
    15: ("EN50549_PT", "Portugal"),
    16: ("PPDS_CR", "Czech Republic"),
    17: ("UNE-206_SP", "Spain"),
    18: ("RD1699_SP", "Spain"),
    19: ("Belgium", "Belgium"),
    20: ("VFR2019_FR", "France"),
    21: ("UTE_FR", "France"),
    22: ("Singapore", "Singapore"),
    23: ("Indonesia", "Indonesia"),
    24: ("Malaysia", "Malaysia"),
    25: ("Cambodia", "Cambodia"),
    26: ("PEA_TH", "Thailand"),
    27: ("MEA_TH", "Thailand"),
    28: ("Sri Lanka", "Sri Lanka"),
    29: ("Pakistan", "Pakistan"),
    30: ("Ireland", "Ireland"),
    31: ("Denmark 3.2.1", "Denmark"),
    32: ("Slovakia", "Slovakia"),
    33: ("Austria", "Austria"),
    34: ("Switzerland", "Switzerland"),
    35: ("Slovenia", "Slovenia"),
    36: ("Hungary", "Hungary"),
    37: ("Serbia", "Serbia"),
    38: ("Croatia", "Croatia"),
    39: ("Turkey", "Türkiye"),
    40: ("Cyprus", "Cyprus"),
    41: ("Bulgaria", "Bulgaria"),
    42: ("Romania", "Romania"),
    43: ("Greece", "Greece"),
    44: ("Latvia", "Latvia"),
    45: ("Lithuania", "Lithuania"),
    46: ("Estonia", "Estonia"),
    47: ("Sweden", "Sweden"),
    48: ("Norway", "Norway"),
    49: ("Finland", "Finland"),
    50: ("Argentina", "Argentina"),
    51: ("Chile BT", "Chile"),
    52: ("Mexico", "Mexico"),
    53: ("USA", "USA"),
    54: ("Hawaii", "Canada"),
    55: ("CQC_CN", "China"),
    56: ("Japan", "Japan"),
    57: ("CQC_CN-1", "China (wide range)"),
    58: ("Local", "India (wide range)"),
    59: ("Saudi Arabia", "Saudi Arabia"),
    60: ("AS4777_AU-2020A", "Australia (A)"),
    61: ("AS4777_AU-2020B", "Australia (B)"),
    62: ("AS4777_AU-2020C", "Australia (C)"),
    63: ("AS4777_NZ-2020", "New Zealand"),
    64: ("CQC_CN-2", "China (wide range 2)"),
    65: ("CEI021_B", "Italy"),
    66: ("CEI021_Areti_A", "Italy"),
    67: ("CEI021_Areti_B", "Italy"),
    68: ("NBR-220_BR2022", "Brazil"),
    69: ("Spain", "Spain"),
    70: ("CQC_CN-3", "China"),
    71: ("Puerto Rico", "Puerto Rico"),
    72: ("G98_NI", "Northern Ireland"),
    73: ("G99_NI", "Northern Ireland"),
    74: ("USA-208", "USA"),
    75: ("VDE4110_DE", "Germany"),
    76: ("KSC8564", "South Korea"),
    77: ("KSC8565", "South Korea"),
    78: ("PR-LUMA", "Puerto Rico"),
    79: ("CEI016", "Italy"),
    80: ("DUBAI", "Dubai"),
    81: ("Denmark 3.2.2", "Denmark"),
    82: ("TR 3.3.1-DK1", "Denmark"),
    83: ("TR 3.3.1-DK2", "Denmark"),
    84: ("Chile MT-A", "Chile"),
    85: ("Chile MT-B", "Chile"),
    86: ("EN50549_FR", "France"),
    87: ("NBR-127_BR2022", "Brazil"),
    88: ("NBR-W220BR2022", "Brazil"),
    89: ("TWN-T", "Taiwan"),
    90: ("TWN-S", "Taiwan"),
    91: ("Israel", "Israel"),
    92: ("EN50549_FR_W", "France"),
    93: ("Test-50Hz", "General"),
    94: ("Test-60Hz", "General"),
    95: ("CQC_CN-4", "China"),
    96: ("EN 50549-2", "Europe"),
    97: ("CQC_CN-5", "China"),
}

# key → (label, unit, hint)
_ROWS: dict[str, tuple[str, str, str]] = {
    "grid_standard_code": ("Grid standard", "", "The grid code the installer chose for your country"),
    "rated_power": ("Rated power", "kW", ""),
    "max_active_power": ("Max AC output", "kW", "The most the inverter puts out; PV above it charges the battery or is clipped"),
    "active_power_derating": ("Active power limit", "%", "100 % = no derating"),
    "fixed_active_power_derate": ("Fixed power derate", "kW", "0 = not set"),
    "installer_export_power_limit": ("Export power limit", "kW", ""),
    "grid_point_power_limit": ("Grid point power limit", "kW", ""),
    "import_current_limit": ("Import current limit", "A", ""),
    "export_current_limit": ("Export current limit", "A", ""),
    "max_charge_current": ("Battery max charge current", "A", ""),
    "max_discharge_current": ("Battery max discharge current", "A", ""),
}


def grid_standard_label(raw: Any) -> str | None:
    try:
        code = int(float(raw))
    except (TypeError, ValueError):
        return None
    name = GRID_STANDARDS.get(code)
    return f"{name[0]} ({name[1]})" if name else f"Code {code}"


def installer_settings_rows(read_state) -> list[dict[str, str]]:
    """Rows for the panel from ``read_state(key) -> state string``; settings the inverter doesn't have are left out."""
    rows: list[dict[str, str]] = []
    for key in INSTALLER_ENTITY_SUFFIXES:
        raw = read_state(key)
        if raw in (None, "", "unknown", "unavailable"):
            continue
        label, unit, hint = _ROWS[key]
        if key == "grid_standard_code":
            value = grid_standard_label(raw) or str(raw)
        else:
            value = f"{raw} {unit}".strip()
        rows.append({"key": key, "label": label, "value": value, "hint": hint})
    return rows

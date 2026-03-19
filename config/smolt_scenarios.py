"""
Four smolt-specific scenario presets for GUI and reporting.
Mirrors SCENARIO_PRESETS from the frontend but with RAS-specific logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class SmoltScenarioPreset:
    id: str
    label_no: str
    description_no: str
    parameter_overrides: Dict[str, Any]
    highest_risk_driver: str


SMOLT_SCENARIO_PRESETS: List[SmoltScenarioPreset] = [
    SmoltScenarioPreset(
        id               = "ras_total_collapse",
        label_no         = "RAS-totalkollaps",
        description_no   = (
            "Biofiltersvikt kombinert med strømbortfall. "
            "Rammer én hel produksjonsavdeling."
        ),
        parameter_overrides = {
            "loss_multiplier":      4.20,
            "bi_trigger":           True,
            "affected_facilities":  1,
            "frequency_multiplier": 1.0,
        },
        highest_risk_driver = "ras_systems",
    ),
    SmoltScenarioPreset(
        id               = "oxygen_crisis",
        label_no         = "Oksygenkrise (4t)",
        description_no   = (
            "Pumpesvikt gir O\u2082 < 6 mg/L i 4 timer. "
            "Tap av 30\u201380\u202f% av ber\u00f8rt generasjon."
        ),
        parameter_overrides = {
            "loss_multiplier":      2.80,
            "bi_trigger":           True,
            "affected_facilities":  1,
            "frequency_multiplier": 1.0,
        },
        highest_risk_driver = "ras_systems",
    ),
    SmoltScenarioPreset(
        id               = "water_contamination",
        label_no         = "Vannforurensning",
        description_no   = (
            "Ekstern forurensing i vannkilde. "
            "Kan ramme hele anlegget. Sjelden men katastrofal."
        ),
        parameter_overrides = {
            "loss_multiplier":      6.50,
            "bi_trigger":           True,
            "affected_facilities":  1,
            "frequency_multiplier": 0.25,
        },
        highest_risk_driver = "environmental",
    ),
    SmoltScenarioPreset(
        id               = "extended_power_outage",
        label_no         = "Str\u00f8mbortfall 48 timer",
        description_no   = (
            "Nett og aggregat feiler. "
            "Hele anlegget mister sirkulasjon. BI-eksponering aktiveres."
        ),
        parameter_overrides = {
            "loss_multiplier":      3.20,
            "bi_trigger":           True,
            "affected_facilities":  1,
            "frequency_multiplier": 1.0,
        },
        highest_risk_driver = "operational",
    ),
]

"""
Smolt / RAS alert rule definitions.

Unlike sea-farming AlertRule (pure data, evaluated by pattern detectors),
SmoltAlertRule carries a triggered_when callable so it can be evaluated
directly against RASMonitoringData without a separate detector class.

15 rules across 4 RAS risk categories:
  - ras_water_quality  (4 rules)
  - biofilter          (4 rules)
  - smolt_health       (4 rules)
  - power_supply       (3 rules)

Weights within each risk_type sum <= 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from c5ai_plus.data_models.smolt_biological_input import RASMonitoringData


@dataclass(frozen=True)
class SmoltAlertRule:
    """
    A named alert rule for RAS / smolt facilities.

    triggered_when(site) returns True when the rule condition is met.
    Returns False (not None) when the required sensor field is missing,
    so missing data never triggers a false positive.
    """
    rule_id:        str
    risk_type:      str
    description:    str
    weight:         float
    triggered_when: Callable[[RASMonitoringData], bool]


# ── RAS Water Quality rules ───────────────────────────────────────────────────

RAS_WATER_QUALITY_RULES: List[SmoltAlertRule] = [
    SmoltAlertRule(
        rule_id        = "ras_o2_critical",
        risk_type      = "ras_water_quality",
        description    = "Dissolved oxygen below critical RAS threshold (< 6.0 mg/L)",
        weight         = 0.35,
        triggered_when = lambda s: (
            s.dissolved_oxygen_mg_l is not None
            and s.dissolved_oxygen_mg_l < 6.0
        ),
    ),
    SmoltAlertRule(
        rule_id        = "ras_o2_warning",
        risk_type      = "ras_water_quality",
        description    = "Dissolved oxygen in warning zone (6.0–7.5 mg/L)",
        weight         = 0.25,
        triggered_when = lambda s: (
            s.dissolved_oxygen_mg_l is not None
            and 6.0 <= s.dissolved_oxygen_mg_l < 7.5
        ),
    ),
    SmoltAlertRule(
        rule_id        = "ras_temp_high",
        risk_type      = "ras_water_quality",
        description    = "Water temperature above RAS stress threshold (> 18 °C)",
        weight         = 0.20,
        triggered_when = lambda s: (
            s.water_temp_c is not None
            and s.water_temp_c > 18.0
        ),
    ),
    SmoltAlertRule(
        rule_id        = "ras_nitrate_load",
        risk_type      = "ras_water_quality",
        description    = "Nitrate concentration indicating biofilter overload (> 12 µmol/L)",
        weight         = 0.20,
        triggered_when = lambda s: (
            s.nitrate_umol_l is not None
            and s.nitrate_umol_l > 12.0
        ),
    ),
]

# ── Biofilter rules ───────────────────────────────────────────────────────────

BIOFILTER_RULES: List[SmoltAlertRule] = [
    SmoltAlertRule(
        rule_id        = "biofilter_nitrite_elevated",
        risk_type      = "biofilter",
        description    = "Nitrite concentration above stress threshold (> 0.1 mg/L)",
        weight         = 0.30,
        triggered_when = lambda s: (
            s.nitrite_mg_l is not None
            and s.nitrite_mg_l > 0.1
        ),
    ),
    SmoltAlertRule(
        rule_id        = "biofilter_ammonia_elevated",
        risk_type      = "biofilter",
        description    = "Total ammonia nitrogen above threshold (> 0.5 mg/L)",
        weight         = 0.25,
        triggered_when = lambda s: (
            s.ammonia_mg_l is not None
            and s.ammonia_mg_l > 0.5
        ),
    ),
    SmoltAlertRule(
        rule_id        = "biofilter_maintenance_overdue",
        risk_type      = "biofilter",
        description    = "Filter maintenance overdue — last service > 90 days ago",
        weight         = 0.25,
        triggered_when = lambda s: (
            s.days_since_last_filter_maintenance is not None
            and s.days_since_last_filter_maintenance > 90
        ),
    ),
    SmoltAlertRule(
        rule_id        = "biofilter_efficiency_low",
        risk_type      = "biofilter",
        description    = "Biofilter efficiency below operational minimum (< 80 %)",
        weight         = 0.20,
        triggered_when = lambda s: (
            s.biofilter_efficiency_pct is not None
            and s.biofilter_efficiency_pct < 80.0
        ),
    ),
]

# ── Smolt Health rules ────────────────────────────────────────────────────────

SMOLT_HEALTH_RULES: List[SmoltAlertRule] = [
    SmoltAlertRule(
        rule_id        = "smolt_cataract_high",
        risk_type      = "smolt_health",
        description    = "Cataract prevalence above welfare threshold (> 5 %)",
        weight         = 0.30,
        triggered_when = lambda s: (
            s.cataract_prevalence_pct is not None
            and s.cataract_prevalence_pct > 5.0
        ),
    ),
    SmoltAlertRule(
        rule_id        = "smolt_agd_elevated",
        risk_type      = "smolt_health",
        description    = "AGD mean gill score above treatment threshold (> 1.5)",
        weight         = 0.25,
        triggered_when = lambda s: (
            s.agd_score_mean is not None
            and s.agd_score_mean > 1.5
        ),
    ),
    SmoltAlertRule(
        rule_id        = "smolt_mortality_elevated",
        risk_type      = "smolt_health",
        description    = "7-day mortality rate above alarm threshold (> 0.5 % / week)",
        weight         = 0.30,
        triggered_when = lambda s: (
            s.mortality_rate_7d_pct is not None
            and s.mortality_rate_7d_pct > 0.5
        ),
    ),
    SmoltAlertRule(
        rule_id        = "smolt_co2_high",
        risk_type      = "smolt_health",
        description    = "CO₂ concentration above cataract risk zone (> 15 ppm)",
        weight         = 0.15,
        triggered_when = lambda s: (
            s.co2_ppm is not None
            and s.co2_ppm > 15.0
        ),
    ),
]

# ── Power Supply rules ────────────────────────────────────────────────────────

POWER_SUPPLY_RULES: List[SmoltAlertRule] = [
    SmoltAlertRule(
        rule_id        = "power_backup_inadequate",
        risk_type      = "power_supply",
        description    = "Backup power capacity below minimum safe level (< 4 hours)",
        weight         = 0.45,
        triggered_when = lambda s: (
            s.backup_power_hours is not None
            and s.backup_power_hours < 4.0
        ),
    ),
    SmoltAlertRule(
        rule_id        = "power_grid_unreliable",
        risk_type      = "power_supply",
        description    = "Grid reliability score below acceptable threshold (< 0.85)",
        weight         = 0.35,
        triggered_when = lambda s: (
            s.grid_reliability_score is not None
            and s.grid_reliability_score < 0.85
        ),
    ),
    SmoltAlertRule(
        rule_id        = "power_test_overdue",
        risk_type      = "power_supply",
        description    = "Backup power system test overdue — last test > 30 days ago",
        weight         = 0.20,
        triggered_when = lambda s: (
            s.last_power_test_days is not None
            and s.last_power_test_days > 30
        ),
    ),
]

# ── Master registry ───────────────────────────────────────────────────────────

ALL_SMOLT_RULES: Dict[str, List[SmoltAlertRule]] = {
    "ras_water_quality": RAS_WATER_QUALITY_RULES,
    "biofilter":         BIOFILTER_RULES,
    "smolt_health":      SMOLT_HEALTH_RULES,
    "power_supply":      POWER_SUPPLY_RULES,
}

ALL_SMOLT_RULES_FLAT: List[SmoltAlertRule] = [
    rule
    for rules in ALL_SMOLT_RULES.values()
    for rule in rules
]


def evaluate_smolt_rules(
    site: RASMonitoringData,
) -> Dict[str, List[SmoltAlertRule]]:
    """
    Evaluate all 15 smolt rules against a single RASMonitoringData site.

    Returns a dict mapping risk_type → list of triggered rules.
    An empty list means no rules fired for that risk type.
    """
    triggered: Dict[str, List[SmoltAlertRule]] = {k: [] for k in ALL_SMOLT_RULES}
    for risk_type, rules in ALL_SMOLT_RULES.items():
        for rule in rules:
            if rule.triggered_when(site):
                triggered[risk_type].append(rule)
    return triggered

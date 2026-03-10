"""
C5AI+ v5.0 – Named Alert Rule Definitions.

Pure data — no logic here. Rules are consumed by detectors.
Each rule has a weight in [0, 1] that scales its contribution to the
precursor_score. All weights within a risk_type should sum <= 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class AlertRule:
    rule_id: str
    risk_type: str
    description: str
    weight: float          # contribution to precursor_score; sum per risk_type <= 1.0


# ── HAB (Harmful Algal Bloom) rules ──────────────────────────────────────────
HAB_RULES: List[AlertRule] = [
    AlertRule(
        rule_id='hab_warm_surface',
        risk_type='hab',
        description='Surface water temperature above HAB threshold (>15°C)',
        weight=0.30,
    ),
    AlertRule(
        rule_id='hab_low_oxygen',
        risk_type='hab',
        description='Dissolved oxygen below safety threshold (<7 mg/L)',
        weight=0.25,
    ),
    AlertRule(
        rule_id='hab_high_nitrate',
        risk_type='hab',
        description='Elevated nitrate concentration indicating algal nutrient load',
        weight=0.20,
    ),
    AlertRule(
        rule_id='hab_high_prior',
        risk_type='hab',
        description='Prior event probability above baseline (>15%)',
        weight=0.25,
    ),
]

# ── Sea lice rules ────────────────────────────────────────────────────────────
LICE_RULES: List[AlertRule] = [
    AlertRule(
        rule_id='lice_warm_water',
        risk_type='lice',
        description='Water temperature above lice reproduction threshold (>10°C)',
        weight=0.25,
    ),
    AlertRule(
        rule_id='lice_elevated_counts',
        risk_type='lice',
        description='Lice counts exceeding treatment trigger threshold',
        weight=0.30,
    ),
    AlertRule(
        rule_id='lice_treatment_fatigue',
        risk_type='lice',
        description='Recent treatment history indicating possible resistance',
        weight=0.25,
    ),
    AlertRule(
        rule_id='lice_open_exposure',
        risk_type='lice',
        description='Open coast exposure with high ambient lice pressure',
        weight=0.20,
    ),
]

# ── Jellyfish rules ───────────────────────────────────────────────────────────
JELLYFISH_RULES: List[AlertRule] = [
    AlertRule(
        rule_id='jellyfish_warm_seasonal',
        risk_type='jellyfish',
        description='Seasonal warm period coinciding with jellyfish bloom window',
        weight=0.35,
    ),
    AlertRule(
        rule_id='jellyfish_current_pattern',
        risk_type='jellyfish',
        description='Onshore current pattern directing bloom toward site',
        weight=0.35,
    ),
    AlertRule(
        rule_id='jellyfish_prior_sightings',
        risk_type='jellyfish',
        description='Recent jellyfish sightings reported in neighbouring fjords',
        weight=0.30,
    ),
]

# ── Pathogen rules ────────────────────────────────────────────────────────────
PATHOGEN_RULES: List[AlertRule] = [
    AlertRule(
        rule_id='pathogen_neighbor_outbreak',
        risk_type='pathogen',
        description='Active pathogen outbreak at neighbouring site within 50 km',
        weight=0.35,
    ),
    AlertRule(
        rule_id='pathogen_high_biomass',
        risk_type='pathogen',
        description='Biomass density above threshold increasing transmission risk',
        weight=0.25,
    ),
    AlertRule(
        rule_id='pathogen_operational_stress',
        risk_type='pathogen',
        description='Recent handling or transport events stressing fish immune system',
        weight=0.20,
    ),
    AlertRule(
        rule_id='pathogen_high_prior',
        risk_type='pathogen',
        description='Prior event probability above baseline (>12%)',
        weight=0.20,
    ),
]

# ── Structural rules ──────────────────────────────────────────────────────────
STRUCTURAL_RULES: List[AlertRule] = [
    AlertRule(
        rule_id='mooring_overload',
        risk_type='mooring_failure',
        description='Mooring inspection score below safety threshold (<0.6)',
        weight=0.30,
    ),
    AlertRule(
        rule_id='net_degradation',
        risk_type='net_integrity',
        description='Net strength residual below acceptable level (<70%)',
        weight=0.25,
    ),
    AlertRule(
        rule_id='cage_deformation',
        risk_type='cage_structural',
        description='Deformation load index elevated above baseline (>0.5)',
        weight=0.20,
    ),
    AlertRule(
        rule_id='anchor_deterioration',
        risk_type='anchor_deterioration',
        description='Anchor line condition deteriorated — score below 0.5',
        weight=0.15,
    ),
    AlertRule(
        rule_id='inspection_overdue',
        risk_type='deformation',
        description='Inspection overdue — last inspection > 180 days ago',
        weight=0.10,
    ),
]

# ── Environmental rules ────────────────────────────────────────────────────────
ENVIRONMENTAL_RULES: List[AlertRule] = [
    AlertRule(
        rule_id='low_oxygen_env',
        risk_type='oxygen_stress',
        description='Dissolved oxygen below critical threshold (<7 mg/L)',
        weight=0.30,
    ),
    AlertRule(
        rule_id='temp_anomaly',
        risk_type='temperature_extreme',
        description='Sea surface temperature outside safe operating range',
        weight=0.25,
    ),
    AlertRule(
        rule_id='high_current_wave',
        risk_type='current_storm',
        description='Current speed or significant wave height exceeds design limit',
        weight=0.25,
    ),
    AlertRule(
        rule_id='ice_formation',
        risk_type='ice',
        description='Ice risk score elevated — risk of equipment damage',
        weight=0.10,
    ),
    AlertRule(
        rule_id='exposure_event',
        risk_type='exposure_anomaly',
        description='Open-coast site with anomalous combined environmental loading',
        weight=0.10,
    ),
]

# ── Operational rules ──────────────────────────────────────────────────────────
OPERATIONAL_RULES: List[AlertRule] = [
    AlertRule(
        rule_id='staffing_gap',
        risk_type='human_error',
        description='Staffing score below minimum safe threshold (<0.6)',
        weight=0.25,
    ),
    AlertRule(
        rule_id='training_deficit',
        risk_type='procedure_failure',
        description='Training compliance below required level (<80%)',
        weight=0.25,
    ),
    AlertRule(
        rule_id='equipment_readiness_low',
        risk_type='equipment_failure',
        description='Equipment readiness score below operational minimum (<0.7)',
        weight=0.20,
    ),
    AlertRule(
        rule_id='high_incident_rate',
        risk_type='incident',
        description='Incident rate in last 12 months above baseline (>1/month)',
        weight=0.15,
    ),
    AlertRule(
        rule_id='maintenance_overdue',
        risk_type='maintenance_backlog',
        description='Maintenance backlog score elevated — deferred work accumulating',
        weight=0.15,
    ),
]

# ── Master rule registry ──────────────────────────────────────────────────────
ALL_RULES: Dict[str, List[AlertRule]] = {
    'hab':                  HAB_RULES,
    'lice':                 LICE_RULES,
    'jellyfish':            JELLYFISH_RULES,
    'pathogen':             PATHOGEN_RULES,
    'mooring_failure':      STRUCTURAL_RULES,
    'net_integrity':        STRUCTURAL_RULES,
    'cage_structural':      STRUCTURAL_RULES,
    'deformation':          STRUCTURAL_RULES,
    'anchor_deterioration': STRUCTURAL_RULES,
    'oxygen_stress':        ENVIRONMENTAL_RULES,
    'temperature_extreme':  ENVIRONMENTAL_RULES,
    'current_storm':        ENVIRONMENTAL_RULES,
    'ice':                  ENVIRONMENTAL_RULES,
    'exposure_anomaly':     ENVIRONMENTAL_RULES,
    'human_error':          OPERATIONAL_RULES,
    'procedure_failure':    OPERATIONAL_RULES,
    'equipment_failure':    OPERATIONAL_RULES,
    'incident':             OPERATIONAL_RULES,
    'maintenance_backlog':  OPERATIONAL_RULES,
}

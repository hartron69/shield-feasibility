"""
C5AI+ v5.0 – Alert Layer Data Models.

Pure JSON-serialisable dataclasses for the early warning / alert system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

ALERT_LEVELS = ('NORMAL', 'WATCH', 'WARNING', 'CRITICAL')
WORKFLOW_STATUSES = ('OPEN', 'ACKNOWLEDGED', 'IN_PROGRESS', 'CLOSED')

# Canonical mapping of all 19 risk_types to their domain
RISK_TYPE_DOMAIN: dict = {
    'hab':                  'biological',
    'lice':                 'biological',
    'jellyfish':            'biological',
    'pathogen':             'biological',
    'mooring_failure':      'structural',
    'net_integrity':        'structural',
    'cage_structural':      'structural',
    'deformation':          'structural',
    'anchor_deterioration': 'structural',
    'oxygen_stress':        'environmental',
    'temperature_extreme':  'environmental',
    'current_storm':        'environmental',
    'ice':                  'environmental',
    'exposure_anomaly':     'environmental',
    'human_error':          'operational',
    'procedure_failure':    'operational',
    'equipment_failure':    'operational',
    'incident':             'operational',
    'maintenance_backlog':  'operational',
}


@dataclass
class PatternSignal:
    """A single precursor signal detected for a site/risk_type combination."""
    site_id: str
    risk_type: str
    signal_name: str
    current_value: float
    baseline_value: float
    z_score: float
    threshold: float
    direction: str       # 'increasing' | 'decreasing'
    triggered: bool

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "PatternSignal":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProbabilityShiftSignal:
    """Detected shift in event probability between two time points."""
    site_id: str
    risk_type: str
    previous_probability: float
    current_probability: float
    absolute_change: float
    relative_change: float
    threshold_crossed: bool
    triggered: bool

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "ProbabilityShiftSignal":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AlertRecord:
    """A single alert record for one site/risk_type combination."""
    alert_id: str                    # uuid4 hex
    site_id: str
    risk_type: str
    alert_type: str                  # 'pattern' | 'probability_shift' | 'composite'
    alert_level: str                 # NORMAL | WATCH | WARNING | CRITICAL
    current_probability: float
    previous_probability: float
    probability_delta: float
    top_drivers: List[str]
    triggered_rules: List[str]
    explanation_text: str
    recommended_actions: List[str]
    workflow_status: str = 'OPEN'
    owner_role: str = 'risk_manager'
    board_visibility: bool = False
    generated_at: str = ''
    domain: str = ''         # populated from RISK_TYPE_DOMAIN; '' = backward compat

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "AlertRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AlertSummary:
    """Per-site summary of alert counts and top risk type."""
    site_id: str
    total_alerts: int
    critical_alerts: int
    warning_alerts: int
    top_risk_type: str
    latest_alert_at: str

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "AlertSummary":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

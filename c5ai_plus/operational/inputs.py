"""C5AI+ v5.0 – Operational domain input schema."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OperationalSiteInput:
    """
    Operational and human-factor condition indicators for a single site.
    """
    site_id: str
    staffing_score: float                   # 0-1; 1 = fully staffed to standard
    training_compliance_pct: float          # 0-100; % of required training completed
    incident_rate_12m: float                # incidents per month over last 12 months
    maintenance_backlog_score: float        # 0-1; 0 = no backlog, 1 = severe backlog
    critical_ops_frequency_per_month: float # frequency of high-risk operations
    equipment_readiness_score: float        # 0-1; 1 = all equipment operational

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> 'OperationalSiteInput':
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

"""C5AI+ v5.0 – Structural domain input schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class StructuralSiteInput:
    """
    Observed and recorded structural condition indicators for a single site.

    All scores on [0, 1] are normalised: 1 = best condition, 0 = worst.
    """
    site_id: str
    net_age_years: float                    # Age of current net (years)
    net_strength_residual_pct: float        # Residual tensile strength (0-100%)
    mooring_inspection_score: float         # 0-1; 1 = recently passed full inspection
    deformation_load_index: float           # 0-1; 0 = no load, 1 = design limit
    anchor_line_condition: float            # 0-1; 1 = new, 0 = severely degraded
    last_inspection_days_ago: int           # Days since last formal structural inspection

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> 'StructuralSiteInput':
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

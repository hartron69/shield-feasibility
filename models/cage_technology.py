"""
models/cage_technology.py — Cage pen technology model for sea localities.

A locality (sjølokalitet) can contain multiple net-pen cages (merder) with
different technologies, each carrying a distinct risk profile expressed as
domain multipliers relative to the open_net baseline (1.0).

Domain multipliers scale the default domain loss fractions:
  < 1.0 = lower risk than baseline
  > 1.0 = higher risk than baseline

Supported cage types:
  open_net     — conventional open sea-cage (baseline)
  semi_closed  — partial water exchange, partial containment
  fully_closed — recirculating or near-zero exchange
  submerged    — submerged cage, wave-sheltered but structurally loaded
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Cage-type domain multiplier table
# ─────────────────────────────────────────────────────────────────────────────

CAGE_DOMAIN_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "open_net": {
        "biological":   1.00,
        "structural":   1.00,
        "environmental": 1.00,
        "operational":  1.00,
    },
    "semi_closed": {
        "biological":   0.75,   # reduced lice / pathogen pressure
        "structural":   0.95,   # slightly modified load paths
        "environmental": 0.80,  # reduced exposure
        "operational":  1.10,   # added mechanical complexity
    },
    "fully_closed": {
        "biological":   0.45,   # major reduction: contained environment
        "structural":   1.20,   # pressure vessels / complex structure
        "environmental": 0.60,  # largely isolated from environment
        "operational":  1.25,   # highest operational complexity
    },
    "submerged": {
        "biological":   0.70,   # reduced surface lice, some pathogen risk
        "structural":   1.15,   # mooring loads, depth pressure
        "environmental": 0.55,  # sheltered from surface weather
        "operational":  1.15,   # complex feed/harvest logistics
    },
}

VALID_CAGE_TYPES = frozenset(CAGE_DOMAIN_MULTIPLIERS.keys())

DOMAINS = ("biological", "structural", "environmental", "operational")


# ─────────────────────────────────────────────────────────────────────────────
# CagePenConfig — one physical cage in a locality
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CagePenConfig:
    """
    Configuration for one net-pen cage (merd) within a locality.

    cage_type must be one of the keys in CAGE_DOMAIN_MULTIPLIERS.
    biomass_tonnes is the stocked biomass (used for weighted aggregation).

    Advanced weighting fields (all optional)
    -----------------------------------------
    biomass_value_nok              — NOK value of biomass in this cage
    consequence_factor             — multiplier on consequence weight (default 1.0)
    operational_complexity_score   — 0–1 scale; None → cage-type default
    structural_criticality_score   — 0–1 scale; None → cage-type default
    single_point_of_failure        — True if this cage is a critical SPOF
    redundancy_level               — 1–5 integer; None → cage-type default
    technology_maturity_score      — 0–1 scale (informational, not yet used in model)
    failure_mode_class             — "proportional" | "threshold" | "binary_high_consequence"
    """
    cage_id: str
    cage_type: str
    biomass_tonnes: float
    volume_m3: Optional[float] = None
    installation_year: Optional[int] = None
    # ── Advanced weighting fields ─────────────────────────────────────────────
    biomass_value_nok: Optional[float] = None
    consequence_factor: Optional[float] = None
    operational_complexity_score: Optional[float] = None
    structural_criticality_score: Optional[float] = None
    single_point_of_failure: bool = False
    redundancy_level: Optional[int] = None
    technology_maturity_score: Optional[float] = None
    failure_mode_class: Optional[str] = None

    def __post_init__(self) -> None:
        if self.cage_type not in VALID_CAGE_TYPES:
            raise ValueError(
                f"Unknown cage_type '{self.cage_type}'. "
                f"Valid types: {sorted(VALID_CAGE_TYPES)}"
            )
        if self.biomass_tonnes <= 0:
            raise ValueError(
                f"biomass_tonnes must be > 0, got {self.biomass_tonnes}"
            )
        # Validate optional advanced fields
        if self.failure_mode_class is not None:
            from config.cage_weighting import VALID_FAILURE_MODE_CLASSES
            if self.failure_mode_class not in VALID_FAILURE_MODE_CLASSES:
                raise ValueError(
                    f"Unknown failure_mode_class '{self.failure_mode_class}'. "
                    f"Valid: {sorted(VALID_FAILURE_MODE_CLASSES)}"
                )
        if self.redundancy_level is not None:
            from config.cage_weighting import VALID_REDUNDANCY_LEVELS
            if self.redundancy_level not in VALID_REDUNDANCY_LEVELS:
                raise ValueError(
                    f"redundancy_level must be in {sorted(VALID_REDUNDANCY_LEVELS)}, "
                    f"got {self.redundancy_level}"
                )
        if self.biomass_value_nok is not None and self.biomass_value_nok < 0:
            raise ValueError(f"biomass_value_nok must be >= 0, got {self.biomass_value_nok}")
        if self.operational_complexity_score is not None:
            if not (0.0 <= self.operational_complexity_score <= 1.0):
                raise ValueError(
                    f"operational_complexity_score must be in [0, 1], "
                    f"got {self.operational_complexity_score}"
                )
        if self.structural_criticality_score is not None:
            if not (0.0 <= self.structural_criticality_score <= 1.0):
                raise ValueError(
                    f"structural_criticality_score must be in [0, 1], "
                    f"got {self.structural_criticality_score}"
                )
        if self.technology_maturity_score is not None:
            if not (0.0 <= self.technology_maturity_score <= 1.0):
                raise ValueError(
                    f"technology_maturity_score must be in [0, 1], "
                    f"got {self.technology_maturity_score}"
                )

    @property
    def domain_multipliers(self) -> Dict[str, float]:
        """Return the domain multipliers for this cage's technology."""
        return CAGE_DOMAIN_MULTIPLIERS[self.cage_type]

    def to_dict(self) -> dict:
        return {
            "cage_id":                      self.cage_id,
            "cage_type":                    self.cage_type,
            "biomass_tonnes":               self.biomass_tonnes,
            "volume_m3":                    self.volume_m3,
            "installation_year":            self.installation_year,
            "biomass_value_nok":            self.biomass_value_nok,
            "consequence_factor":           self.consequence_factor,
            "operational_complexity_score": self.operational_complexity_score,
            "structural_criticality_score": self.structural_criticality_score,
            "single_point_of_failure":      self.single_point_of_failure,
            "redundancy_level":             self.redundancy_level,
            "technology_maturity_score":    self.technology_maturity_score,
            "failure_mode_class":           self.failure_mode_class,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CagePenConfig":
        return cls(
            cage_id=d["cage_id"],
            cage_type=d["cage_type"],
            biomass_tonnes=float(d["biomass_tonnes"]),
            volume_m3=d.get("volume_m3"),
            installation_year=d.get("installation_year"),
            biomass_value_nok=d.get("biomass_value_nok"),
            consequence_factor=d.get("consequence_factor"),
            operational_complexity_score=d.get("operational_complexity_score"),
            structural_criticality_score=d.get("structural_criticality_score"),
            single_point_of_failure=d.get("single_point_of_failure", False),
            redundancy_level=d.get("redundancy_level"),
            technology_maturity_score=d.get("technology_maturity_score"),
            failure_mode_class=d.get("failure_mode_class"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Aggregation helpers
# ─────────────────────────────────────────────────────────────────────────────

def compute_locality_domain_multipliers(
    cages: List[CagePenConfig],
) -> Dict[str, float]:
    """
    Compute biomass-weighted average domain multipliers for a locality.

    Returns a dict with keys 'biological', 'structural', 'environmental',
    'operational' — each value is the weighted mean of per-cage multipliers.

    Raises ValueError if cages is empty.
    """
    if not cages:
        raise ValueError("cages must be a non-empty list")

    total_biomass = sum(c.biomass_tonnes for c in cages)
    if total_biomass == 0:
        raise ValueError("Total cage biomass is zero — cannot compute weights")

    result: Dict[str, float] = {}
    for domain in DOMAINS:
        weighted_sum = sum(
            c.biomass_tonnes * c.domain_multipliers[domain] for c in cages
        )
        result[domain] = weighted_sum / total_biomass

    return result


def cage_type_summary(cages: List[CagePenConfig]) -> Dict[str, float]:
    """
    Return total biomass per cage type for a locality (for UI display).

    Example: {"open_net": 1200.0, "semi_closed": 800.0}
    """
    summary: Dict[str, float] = {}
    for cage in cages:
        summary[cage.cage_type] = summary.get(cage.cage_type, 0.0) + cage.biomass_tonnes
    return summary

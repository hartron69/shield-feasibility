"""
models/locality_risk_profile.py

Unified risk profile for a single sea locality.

LocalityRiskProfile is the single source of truth for per-locality risk
in the Shield Risk Platform. It combines:
  - Live Risk signals (domain scores, confidence)
  - Static locality metadata (name, region, biomass, exposure)
  - Cage portfolio / advanced cage weighting where available

Designed to be the foundation for:
  - locality-level Monte Carlo (later sprint)
  - portfolio aggregation
  - mitigation application
  - cell portfolio optimisation
  - historical comparison
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


DOMAINS = ("biological", "structural", "environmental", "operational")

# Fixed domain weights from the Live Risk scoring model (see live_risk_mock._compute_risk)
LIVE_RISK_SCALE_FACTORS: Dict[str, float] = {
    "biological":    0.35,
    "structural":    0.25,
    "environmental": 0.25,
    "operational":   0.15,
}


@dataclass
class DomainRiskScores:
    """Current domain-level risk scores (0–100) from the Live Risk feed."""

    biological: float
    structural: float
    environmental: float
    operational: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "biological":    self.biological,
            "structural":    self.structural,
            "environmental": self.environmental,
            "operational":   self.operational,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DomainRiskScores":
        return cls(
            biological=float(d["biological"]),
            structural=float(d["structural"]),
            environmental=float(d["environmental"]),
            operational=float(d["operational"]),
        )


@dataclass
class DomainRiskWeights:
    """
    Normalized contribution fractions of each domain to the current total risk score.

    Computed as: contribution_i = score_i × scale_factor_i, then
    weight_i = contribution_i / sum(all contributions).

    Reflects "how much of today's risk is driven by each domain."
    """

    biological: float
    structural: float
    environmental: float
    operational: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "biological":    self.biological,
            "structural":    self.structural,
            "environmental": self.environmental,
            "operational":   self.operational,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DomainRiskWeights":
        return cls(
            biological=float(d["biological"]),
            structural=float(d["structural"]),
            environmental=float(d["environmental"]),
            operational=float(d["operational"]),
        )


@dataclass
class RiskSourceSummary:
    """Records which data sources contributed to the profile."""

    live_risk_available: bool
    cage_portfolio_available: bool
    advanced_weighting_available: bool
    bw_live: bool
    sources_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "live_risk_available":        self.live_risk_available,
            "cage_portfolio_available":   self.cage_portfolio_available,
            "advanced_weighting_available": self.advanced_weighting_available,
            "bw_live":                    self.bw_live,
            "sources_used":               list(self.sources_used),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RiskSourceSummary":
        return cls(
            live_risk_available=bool(d["live_risk_available"]),
            cage_portfolio_available=bool(d["cage_portfolio_available"]),
            advanced_weighting_available=bool(d["advanced_weighting_available"]),
            bw_live=bool(d["bw_live"]),
            sources_used=list(d.get("sources_used", [])),
        )


@dataclass
class LocalityRiskProfile:
    """
    Full risk profile for one locality.

    Combines Live Risk signals, locality metadata, and cage portfolio data
    into a single, inspectable object with explicit provenance.
    """

    # ── Identity ────────────────────────────────────────────────────────────────
    locality_id:   str
    locality_name: str
    company_name:  str
    region:        str
    drift_type:    str          # "sjø" for sea sites

    # ── Exposure & biomass ──────────────────────────────────────────────────────
    biomass_tonnes:    float
    biomass_value_nok: float
    exposure_factor:   float

    # ── Cage portfolio ──────────────────────────────────────────────────────────
    cage_count:         int
    cage_weighting_mode: str    # "advanced" | "biomass_only" | "none"

    # ── Risk signal ─────────────────────────────────────────────────────────────
    domain_scores:      DomainRiskScores
    domain_weights:     DomainRiskWeights   # normalized contribution fractions
    domain_multipliers: Dict[str, float]    # cage-derived or uniform 1.0 defaults
    scale_factors:      Dict[str, float]    # fixed model-level domain weights

    # ── Pattern detection ───────────────────────────────────────────────────────
    concentration_flags: List[str]          # e.g. ["high_biological_dominance", "high_exposure"]
    top_risk_drivers:    List[str]          # domains sorted by weighted contribution (desc)

    # ── Confidence & provenance ─────────────────────────────────────────────────
    confidence_level: str        # "high" | "medium" | "low"
    confidence_notes: List[str]

    source_summary: RiskSourceSummary
    used_defaults:  List[str]    # explicitly named when defaults are substituted

    # ── Arbitrary metadata ──────────────────────────────────────────────────────
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── Serialisation ───────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "locality_id":          self.locality_id,
            "locality_name":        self.locality_name,
            "company_name":         self.company_name,
            "region":               self.region,
            "drift_type":           self.drift_type,
            "biomass_tonnes":       self.biomass_tonnes,
            "biomass_value_nok":    self.biomass_value_nok,
            "exposure_factor":      self.exposure_factor,
            "cage_count":           self.cage_count,
            "cage_weighting_mode":  self.cage_weighting_mode,
            "domain_scores":        self.domain_scores.to_dict(),
            "domain_weights":       self.domain_weights.to_dict(),
            "domain_multipliers":   dict(self.domain_multipliers),
            "scale_factors":        dict(self.scale_factors),
            "concentration_flags":  list(self.concentration_flags),
            "top_risk_drivers":     list(self.top_risk_drivers),
            "confidence_level":     self.confidence_level,
            "confidence_notes":     list(self.confidence_notes),
            "source_summary":       self.source_summary.to_dict(),
            "used_defaults":        list(self.used_defaults),
            "metadata":             dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LocalityRiskProfile":
        return cls(
            locality_id=d["locality_id"],
            locality_name=d["locality_name"],
            company_name=d["company_name"],
            region=d["region"],
            drift_type=d["drift_type"],
            biomass_tonnes=float(d["biomass_tonnes"]),
            biomass_value_nok=float(d["biomass_value_nok"]),
            exposure_factor=float(d["exposure_factor"]),
            cage_count=int(d["cage_count"]),
            cage_weighting_mode=d["cage_weighting_mode"],
            domain_scores=DomainRiskScores.from_dict(d["domain_scores"]),
            domain_weights=DomainRiskWeights.from_dict(d["domain_weights"]),
            domain_multipliers=dict(d["domain_multipliers"]),
            scale_factors=dict(d["scale_factors"]),
            concentration_flags=list(d["concentration_flags"]),
            top_risk_drivers=list(d["top_risk_drivers"]),
            confidence_level=d["confidence_level"],
            confidence_notes=list(d["confidence_notes"]),
            source_summary=RiskSourceSummary.from_dict(d["source_summary"]),
            used_defaults=list(d["used_defaults"]),
            metadata=dict(d.get("metadata", {})),
        )

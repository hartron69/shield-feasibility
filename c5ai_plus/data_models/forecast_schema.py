"""
C5AI+ v5.0 – Risk Forecast Output Schema.

This module defines the canonical output format produced by C5AI+ and
consumed by the PCC Feasibility Tool's MonteCarloEngine.

The schema is defined as both a dataclass hierarchy (for internal use)
and a JSON-serialisable dict structure (for file-based exchange).

Canonical file: risk_forecast.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS

# ── Risk type literals ────────────────────────────────────────────────────────
RISK_TYPES = ("hab", "lice", "jellyfish", "pathogen")

# ── Data quality flag literals ─────────────────────────────────────────────────
DATA_QUALITY_FLAGS = ("SUFFICIENT", "LIMITED", "POOR", "PRIOR_ONLY")


@dataclass
class RiskTypeForecast:
    """
    Annual risk forecast for a single risk type at a single site.

    Attributes
    ----------
    risk_type : str
        One of: "hab", "lice", "jellyfish", "pathogen".
    year : int
        Forecast year (1-indexed relative to current year).
    event_probability : float
        Probability of at least one significant loss event (0–1).
        After mitigation this holds the adjusted value; use
        baseline_event_probability to recover the original.
    expected_loss_mean : float
        Expected economic loss in NOK (mean of distribution).
        After mitigation this holds the adjusted value; use
        baseline_expected_loss_mean to recover the original.
    expected_loss_p50 : float
        Median expected loss in NOK.
    expected_loss_p90 : float
        90th percentile expected loss in NOK.
    confidence_score : float
        Model confidence (0–1). Low when data is sparse.
    data_quality_flag : str
        "SUFFICIENT", "LIMITED", "POOR", or "PRIOR_ONLY".
    model_used : str
        Identifier of the model that produced this forecast.

    Mitigation provenance (all Optional, populated by
    apply_mitigations_to_forecast)
    ---------------------------------------------------
    baseline_event_probability : float or None
        Original event_probability before any mitigation was applied.
    baseline_expected_loss_mean : float or None
        Original expected_loss_mean before any mitigation was applied.
    applied_mitigations : List[str]
        Names of MitigationActions that modified this forecast entry.
    """
    risk_type: str
    year: int
    event_probability: float
    expected_loss_mean: float
    expected_loss_p50: float
    expected_loss_p90: float
    confidence_score: float
    data_quality_flag: str
    model_used: str = "prior"
    # Mitigation provenance – all default to None / [] for backward compat
    baseline_event_probability: Optional[float] = None
    baseline_expected_loss_mean: Optional[float] = None
    applied_mitigations: List[str] = field(default_factory=list)
    # Learning loop fields – all optional for backward compat
    baseline_probability: Optional[float] = None    # prior/static estimate
    adjusted_probability: Optional[float] = None    # Bayesian posterior
    brier_score_recent: Optional[float] = None
    severity_mae_recent: Optional[float] = None


@dataclass
class SiteForecast:
    """
    All risk type forecasts for a single site across all forecast years.

    Attributes
    ----------
    site_id : str
    site_name : str
    annual_forecasts : List[RiskTypeForecast]
        Flat list – one entry per (year, risk_type) combination.
    """
    site_id: str
    site_name: str
    annual_forecasts: List[RiskTypeForecast] = field(default_factory=list)

    def get_forecast(self, risk_type: str, year: int) -> Optional[RiskTypeForecast]:
        """Return the forecast for a specific (risk_type, year) pair, or None."""
        for f in self.annual_forecasts:
            if f.risk_type == risk_type and f.year == year:
                return f
        return None

    def total_expected_loss_nok(self, year: int) -> float:
        """Sum of expected losses across all risk types for a given year."""
        return sum(
            f.expected_loss_mean
            for f in self.annual_forecasts
            if f.year == year
        )


@dataclass
class OperatorAggregate:
    """
    Operator-level aggregated forecast – consumed directly by MonteCarloEngine.

    Attributes
    ----------
    annual_expected_loss_by_type : Dict[str, float]
        Mean annual expected loss per risk type (NOK), averaged over forecast years.
    total_expected_annual_loss : float
        Sum of all risk types. MonteCarloEngine uses this as its primary input.
    c5ai_vs_static_ratio : float
        Ratio of C5AI+ predicted loss to the static Poisson model's estimate.
        Used as a multiplicative scale factor in the simulation.
        A value of 1.0 means C5AI+ agrees with the static model.
    loss_breakdown_fractions : Dict[str, float]
        Fraction of total expected loss attributable to each risk type.
        Sums to 1.0. Used for disaggregated reporting.
    """
    annual_expected_loss_by_type: Dict[str, float]
    total_expected_annual_loss: float
    c5ai_vs_static_ratio: float
    loss_breakdown_fractions: Dict[str, float]
    # Preserved pre-mitigation total (populated by apply_mitigations_to_forecast)
    baseline_total_expected_annual_loss: Optional[float] = None


@dataclass
class ForecastMetadata:
    """
    Provenance and quality metadata for the forecast file.
    """
    model_version: str
    generated_at: str          # ISO-8601 UTC timestamp
    operator_id: str
    operator_name: str
    forecast_horizon_years: int
    overall_confidence: str    # "high", "medium", "low"
    overall_data_quality: str  # DATA_QUALITY_FLAGS value
    sites_included: List[str]
    warnings: List[str] = field(default_factory=list)
    # Applied mitigation summary (populated by apply_mitigations_to_forecast)
    applied_mitigations: List[str] = field(default_factory=list)
    # Learning loop metadata – all optional for backward compat
    learning_status: str = "cold"
    cycles_completed: int = 0
    last_retrain_at: Optional[str] = None
    probability_model_versions: Dict[str, str] = field(default_factory=dict)
    severity_model_versions: Dict[str, str] = field(default_factory=dict)


@dataclass
class RiskForecast:
    """
    Complete C5AI+ forecast package – top-level container.

    This is the object serialised to risk_forecast.json and deserialised
    by the PCC Feasibility Tool.

    Attributes
    ----------
    metadata : ForecastMetadata
    site_forecasts : List[SiteForecast]
    operator_aggregate : OperatorAggregate
        Pre-computed aggregates ready for MonteCarloEngine consumption.
    """
    metadata: ForecastMetadata
    site_forecasts: List[SiteForecast]
    operator_aggregate: OperatorAggregate

    # ── Convenience accessors ─────────────────────────────────────────────

    @property
    def scale_factor(self) -> float:
        """Shorthand: how much to scale the static Monte Carlo loss estimates."""
        return self.operator_aggregate.c5ai_vs_static_ratio

    @property
    def total_expected_annual_loss(self) -> float:
        return self.operator_aggregate.total_expected_annual_loss

    @property
    def loss_fractions(self) -> Dict[str, float]:
        return self.operator_aggregate.loss_breakdown_fractions

    # ── Serialisation ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Convert to a plain dict suitable for JSON serialisation."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialise to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "RiskForecast":
        """Reconstruct a RiskForecast from a plain dict (loaded from JSON)."""
        site_forecasts = []
        _rtf_fields = {f for f in RiskTypeForecast.__dataclass_fields__}
        for sd in data["site_forecasts"]:
            forecasts = [
                RiskTypeForecast(**{k: v for k, v in f.items() if k in _rtf_fields})
                for f in sd["annual_forecasts"]
            ]
            site_forecasts.append(
                SiteForecast(
                    site_id=sd["site_id"],
                    site_name=sd["site_name"],
                    annual_forecasts=forecasts,
                )
            )

        _agg_fields = {f for f in OperatorAggregate.__dataclass_fields__}
        agg = OperatorAggregate(
            **{k: v for k, v in data["operator_aggregate"].items() if k in _agg_fields}
        )
        _meta_fields = {f for f in ForecastMetadata.__dataclass_fields__}
        meta = ForecastMetadata(
            **{k: v for k, v in data["metadata"].items() if k in _meta_fields}
        )
        return cls(metadata=meta, site_forecasts=site_forecasts, operator_aggregate=agg)

    @classmethod
    def from_json_file(cls, path: str) -> "RiskForecast":
        """Load a RiskForecast from a JSON file on disk."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)

"""
Input data schema and validation for the PCC Feasibility Tool.

All monetary values are in USD unless otherwise stated.
"""

from __future__ import annotations

import dataclasses as _dc
from dataclasses import dataclass, field
from typing import List, Optional
import json
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Sub-schemas
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SiteProfile:
    """A single production site (farm, pen cluster, hatchery, etc.)."""
    name: str
    location: str
    species: str                          # e.g. "Atlantic Salmon", "Sea Bass"
    biomass_tonnes: float                 # Maximum standing biomass
    biomass_value_per_tonne: float        # $ / tonne (market price)
    equipment_value: float                # $ – nets, feeders, boats, cages
    infrastructure_value: float           # $ – moorings, buildings, pipes
    annual_revenue: float                 # $ – site revenue
    site_type: str = "production"         # production | processing | hatchery | land_based | support

    @property
    def is_biomass_site(self) -> bool:
        """True for site types that carry standing biomass risk."""
        return self.site_type in {"production", "hatchery", "land_based"}

    @property
    def is_revenue_site(self) -> bool:
        """True for site types that generate direct revenue."""
        return self.site_type in {"production", "processing", "hatchery"}

    @property
    def total_insured_value(self) -> float:
        biomass_value = self.biomass_tonnes * self.biomass_value_per_tonne
        return biomass_value + self.equipment_value + self.infrastructure_value


@dataclass
class HistoricalLossRecord:
    """One historical loss event."""
    year: int
    event_type: str       # "mortality", "property", "liability", "business_interruption"
    gross_loss: float     # $ – total economic loss before insurance recovery
    insured_loss: float   # $ – amount paid by insurer
    retained_loss: float  # $ – operator self-absorbed


@dataclass
class CurrentInsuranceProgram:
    """Operator's existing insurance structure."""
    annual_premium: float              # $ total premium paid
    per_occurrence_deductible: float   # $
    annual_aggregate_deductible: float # $
    coverage_limit: float             # $ per occurrence
    aggregate_limit: float            # $ per year
    coverage_lines: List[str]         # e.g. ["Mortality", "Property", "BI"]
    insurer_names: List[str]
    current_loss_ratio: float          # Historical LR (losses / premium)
    market_rating_trend: float         # Annual premium change rate (e.g. 0.05 = +5%)


@dataclass
class FinancialProfile:
    """Operator financial standing – key metrics for captive suitability."""
    annual_revenue: float              # $ consolidated
    ebitda: float                      # $
    total_assets: float                # $
    net_equity: float                  # $
    credit_rating: Optional[str]       # e.g. "BBB", "BB+", or None
    free_cash_flow: float              # $ – available to fund capital
    years_in_operation: int


@dataclass
class RiskParameters:
    """
    Statistical parameters governing loss frequency and severity.
    If historical_losses is provided these can be estimated automatically;
    otherwise the operator / actuary supplies them directly.
    """
    # Frequency (Poisson lambda)
    expected_annual_events: float          # Average number of loss-producing events/yr
    # Severity (LogNormal parameters)
    mean_loss_severity: float              # $ – expected cost per event
    cv_loss_severity: float               # Coefficient of variation of severity
    # Tail behaviour
    catastrophe_probability: float        # Annual probability of a CAT event
    catastrophe_loss_multiplier: float    # CAT loss as multiple of mean severity
    # Correlations / dependencies
    inter_site_correlation: float         # 0-1  correlation between site losses
    # Business interruption
    bi_trigger_threshold: float           # $ loss that triggers BI cover
    bi_daily_revenue_loss: float          # $ per day of interruption
    bi_average_interruption_days: float   # Expected downtime days per major event


@dataclass
class OperatorInput:
    """Top-level operator data container – primary input to all models."""
    # ── Identity ─────────────────────────────────────────────────────────────
    name: str
    registration_number: str
    country: str
    reporting_currency: str

    # ── Sites ─────────────────────────────────────────────────────────────────
    sites: List[SiteProfile]

    # ── Insurance ─────────────────────────────────────────────────────────────
    current_insurance: CurrentInsuranceProgram

    # ── Historical losses (at least 3 years recommended) ─────────────────────
    historical_losses: List[HistoricalLossRecord]

    # ── Financials ────────────────────────────────────────────────────────────
    financials: FinancialProfile

    # ── Risk parameters ───────────────────────────────────────────────────────
    risk_params: RiskParameters

    # ── Strategy preferences (optional overrides) ─────────────────────────────
    captive_domicile_preference: Optional[str] = None   # e.g. "Cayman", "Guernsey"
    management_commitment_years: int = 5
    willing_to_provide_capital: bool = True
    has_risk_manager: bool = False
    governance_maturity: str = "developing"  # "basic" | "developing" | "mature"

    # ── C5AI+ integration (optional) ──────────────────────────────────────────
    # Path to a risk_forecast.json produced by C5AI+ v5.0.
    # When provided, MonteCarloEngine uses dynamic biological risk estimates
    # instead of the static Compound Poisson model.
    # Leave None (or omit from JSON) to use the static model.
    c5ai_forecast_path: Optional[str] = None

    # Biological operational readiness score (0–100), set by operator.
    # Used in suitability scoring criterion 6.
    # 0 = no biological risk management capability.
    # 100 = fully integrated monitoring, response protocols, and trained staff.
    bio_readiness_score: Optional[int] = None  # None = derived from data quality

    # ── Mitigation actions (optional) ─────────────────────────────────────────
    # List of mitigation action keys from PREDEFINED_MITIGATIONS or custom
    # action names.  Used by MitigationAnalyzer to compute adjusted loss metrics.
    # Example: ["stronger_nets", "lice_barriers", "environmental_sensors"]
    mitigation_actions: List[str] = None  # type: ignore[assignment]

    # ── Retention structure (optional) ────────────────────────────────────────
    # Override default retention parameters for captive structure modelling.
    # Dict with keys: "per_occurrence_retention", "annual_aggregate_retention".
    # If None, defaults are taken from current_insurance deductible fields.
    retention_structure: Optional[dict] = None

    def __post_init__(self):
        if self.mitigation_actions is None:
            object.__setattr__(self, 'mitigation_actions', [])

    # ── Computed aggregates ───────────────────────────────────────────────────
    @property
    def total_insured_value(self) -> float:
        return sum(s.total_insured_value for s in self.sites)

    @property
    def total_annual_revenue(self) -> float:
        return sum(s.annual_revenue for s in self.sites)

    @property
    def historical_annual_losses(self) -> List[float]:
        """Gross loss by year (aggregated across all events in each year)."""
        by_year: dict[int, float] = {}
        for rec in self.historical_losses:
            by_year[rec.year] = by_year.get(rec.year, 0.0) + rec.gross_loss
        return list(by_year.values())

    @property
    def average_historical_loss(self) -> float:
        losses = self.historical_annual_losses
        return sum(losses) / len(losses) if losses else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Validation & Factory
# ─────────────────────────────────────────────────────────────────────────────

def validate_input(raw: dict) -> OperatorInput:
    """Parse and validate raw JSON dict into an OperatorInput object."""

    def _site(d: dict) -> SiteProfile:
        kwargs = {}
        for k, f in SiteProfile.__dataclass_fields__.items():
            if k in d:
                kwargs[k] = d[k]
            elif f.default is not _dc.MISSING:
                kwargs[k] = f.default
        return SiteProfile(**kwargs)

    def _loss_record(d: dict) -> HistoricalLossRecord:
        return HistoricalLossRecord(**{k: d[k] for k in HistoricalLossRecord.__dataclass_fields__})

    def _insurance(d: dict) -> CurrentInsuranceProgram:
        return CurrentInsuranceProgram(**{k: d[k] for k in CurrentInsuranceProgram.__dataclass_fields__})

    def _financials(d: dict) -> FinancialProfile:
        return FinancialProfile(**{k: d[k] for k in FinancialProfile.__dataclass_fields__})

    def _risk_params(d: dict) -> RiskParameters:
        return RiskParameters(**{k: d[k] for k in RiskParameters.__dataclass_fields__})

    sites = [_site(s) for s in raw["sites"]]
    historical_losses = [_loss_record(r) for r in raw.get("historical_losses", [])]
    insurance = _insurance(raw["current_insurance"])
    financials = _financials(raw["financials"])
    risk_params = _risk_params(raw["risk_params"])

    # Basic sanity checks
    if not sites:
        raise ValueError("At least one site must be specified.")
    if insurance.annual_premium <= 0:
        raise ValueError("Annual premium must be positive.")
    if risk_params.expected_annual_events < 0:
        raise ValueError("Expected annual events cannot be negative.")

    return OperatorInput(
        name=raw["name"],
        registration_number=raw.get("registration_number", "N/A"),
        country=raw["country"],
        reporting_currency=raw.get("reporting_currency", "USD"),
        sites=sites,
        current_insurance=insurance,
        historical_losses=historical_losses,
        financials=financials,
        risk_params=risk_params,
        captive_domicile_preference=raw.get("captive_domicile_preference"),
        management_commitment_years=raw.get("management_commitment_years", 5),
        willing_to_provide_capital=raw.get("willing_to_provide_capital", True),
        has_risk_manager=raw.get("has_risk_manager", False),
        governance_maturity=raw.get("governance_maturity", "developing"),
        c5ai_forecast_path=raw.get("c5ai_forecast_path"),
        bio_readiness_score=raw.get("bio_readiness_score"),
    )


def load_from_file(path: str) -> OperatorInput:
    with open(path, "r") as fh:
        raw = json.load(fh)
    return validate_input(raw)

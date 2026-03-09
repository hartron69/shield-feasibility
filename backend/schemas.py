"""
Shield Risk Platform – Pydantic request / response models for the FastAPI backend.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────────────

class OperatorProfileInput(BaseModel):
    name: str = "Nordic Aqua Partners AS"
    country: str = "Norge"
    n_sites: int = Field(default=3, ge=1, le=20)
    total_biomass_tonnes: float = Field(default=9200.0, gt=0)
    # ── Biomass valuation ─────────────────────────────────────────────────────
    # applied value used in all downstream calculations
    biomass_value_per_tonne: float = Field(default=64_800.0, gt=0)
    # reference-price formula inputs (for suggestion and transparency)
    reference_price_per_kg: float = Field(
        default=80.0, gt=0,
        description="Spot/reference price in NOK per kg at harvest weight",
    )
    realisation_factor: float = Field(
        default=0.90, ge=0.5, le=1.2,
        description="Expected net realisation as a fraction of reference price (0.90 = 90%)",
    )
    prudence_haircut: float = Field(
        default=0.10, ge=0.0, le=0.5,
        description="Insurance prudence reduction (0.10 = 10% below realised value)",
    )
    # explicit override: when set, replaces biomass_value_per_tonne in the builder
    biomass_value_per_tonne_override: Optional[float] = Field(
        default=None,
        description="Manual override for applied biomass value (NOK/tonne). "
                    "When provided, this takes priority over biomass_value_per_tonne.",
    )
    annual_revenue_nok: float = Field(default=897_000_000.0, gt=0)
    annual_premium_nok: float = Field(default=19_500_000.0, gt=0)


class ModelSettingsInput(BaseModel):
    n_simulations: int = Field(default=5_000, ge=100, le=100_000)
    domain_correlation: str = Field(
        default="expert_default",
        description="One of: independent, expert_default, low, moderate",
    )
    generate_pdf: bool = True
    use_history_calibration: bool = Field(
        default=False,
        description=(
            "When True and ≥3 historical loss records are present, calibrate "
            "mean_loss_severity and expected_annual_events from observed data "
            "instead of template TIV scaling."
        ),
    )


class StrategySettingsInput(BaseModel):
    strategy: str = Field(
        default="pcc_captive",
        description="One of: full_insurance, hybrid, pcc_captive, self_insurance",
    )
    retention_nok: Optional[float] = None


class PoolingSettingsInput(BaseModel):
    enabled: bool = False
    n_members: int = Field(default=4, ge=2, le=10)
    inter_member_correlation: float = Field(default=0.25, ge=0.0, le=0.95)
    similarity_spread: float = Field(default=0.15, ge=0.0, le=0.50)
    pooled_retention_nok: float = Field(default=25_000_000.0, gt=0)
    pooled_ri_limit_nok: float = Field(default=400_000_000.0, gt=0)
    pooled_ri_loading_factor: float = Field(default=1.40, ge=1.0, le=3.0)
    shared_admin_saving_pct: float = Field(default=0.20, ge=0.0, le=0.50)
    allocation_basis: str = Field(default="expected_loss")


class MitigationInput(BaseModel):
    selected_actions: List[str] = Field(default_factory=list)


class FeasibilityRequest(BaseModel):
    operator_profile: OperatorProfileInput = Field(default_factory=OperatorProfileInput)
    model_settings: ModelSettingsInput = Field(default_factory=ModelSettingsInput)
    strategy_settings: StrategySettingsInput = Field(default_factory=StrategySettingsInput)
    mitigation: MitigationInput = Field(default_factory=MitigationInput)
    pooling_settings: PoolingSettingsInput = Field(default_factory=PoolingSettingsInput)
    # Alias kept for backward compat (Sprint 8 spec)
    output_options: Optional[Dict] = None


# ─────────────────────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────────────────────

class KPISummary(BaseModel):
    expected_annual_loss: float
    p95_loss: float
    p99_loss: float
    scr: float
    recommended_strategy: str
    verdict: str
    composite_score: float
    confidence_level: str


class ScenarioBlock(BaseModel):
    summary: KPISummary
    charts: Dict[str, str] = Field(default_factory=dict)   # key → base64 PNG
    criterion_scores: List[Dict] = Field(default_factory=list)


class ComparisonBlock(BaseModel):
    expected_loss_delta: float
    expected_loss_delta_pct: float
    p95_delta: float
    p99_delta: float
    scr_delta: float
    annual_cost_saving: float
    top_benefit_domains: List[str]
    narrative: str


class ReportBlock(BaseModel):
    available: bool
    pdf_url: Optional[str] = None


class MetadataBlock(BaseModel):
    domain_correlation_active: bool
    mitigation_active: bool
    n_simulations: int


class BiomassValuationSummary(BaseModel):
    """Transparency record for how the applied biomass value was determined."""
    reference_price_per_kg: float
    realisation_factor: float
    prudence_haircut: float
    suggested_biomass_value_per_tonne: float
    applied_biomass_value_per_tonne: float
    user_overridden: bool


class SiteAllocationRow(BaseModel):
    name: str
    biomass_tonnes: int
    biomass_value_nok: float
    equipment_value_nok: float
    infrastructure_value_nok: float
    annual_revenue_nok: float
    tiv_nok: float
    weight_pct: float


class AllocationSummary(BaseModel):
    template_exposure_nok: float
    user_exposure_nok: float
    tiv_ratio: float
    risk_severity_scaled: float
    risk_events_scaled: float
    financial_ratios: Dict[str, float]
    sites: List[SiteAllocationRow]
    biomass_valuation: Optional[BiomassValuationSummary] = None
    # History calibration tracking (populated by operator_builder)
    calibration_active: bool = False
    calibration_mode: str = "none"   # "none" | "portfolio" | "domain"
    calibrated_parameters: Dict[str, float] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


# ── History domain mapping ──────────────────────────────────────────────────
# Canonical event_type → risk domain map.  Used by history_analytics and tests.
HISTORY_DOMAIN_MAP: Dict[str, str] = {
    "mortality":             "biological",
    "property":              "structural",
    "business_interruption": "operational",
}


class HistoryEventRow(BaseModel):
    year: int
    event_type: str
    domain: str          # Derived from event_type via HISTORY_DOMAIN_MAP; "unknown" if unmapped
    gross_loss: float
    insured_loss: float
    retained_loss: float


class HistoricalDomainSummary(BaseModel):
    """Aggregated loss statistics for a single risk domain."""
    domain: str
    event_count: int
    total_gross_loss: float
    total_insured_loss: float
    total_retained_loss: float
    mean_severity: float             # total_gross_loss / event_count
    events_per_year: float           # event_count / n_years (full history window)
    loss_share_pct: float            # domain gross / portfolio gross × 100
    years_with_events: List[int]


class HistoricalLossSummary(BaseModel):
    """Rich history summary with domain breakdown (replaces HistorySummary in API response)."""
    # ── Record metadata ───────────────────────────────────────────────────────
    history_loaded: bool
    history_source: str              # "template" | "user_provided"
    record_count: int
    years_covered: List[int]
    n_years_observed: int

    # ── Portfolio aggregates ──────────────────────────────────────────────────
    portfolio_total_gross: float
    portfolio_total_insured: float
    portfolio_total_retained: float
    portfolio_mean_severity: float
    portfolio_events_per_year: float

    # ── Domain breakdown ──────────────────────────────────────────────────────
    domain_summaries: List[HistoricalDomainSummary]
    mapping_warnings: List[str] = Field(default_factory=list)

    # ── Calibration metadata ──────────────────────────────────────────────────
    calibration_active: bool
    calibration_source: str          # "historical_loss_records" | "historical_domain_calibration" | "none"
    calibration_mode: str            # "none" | "portfolio" | "domain"
    calibrated_parameters: Dict[str, float] = Field(default_factory=dict)

    # ── Raw records (with domain field) ──────────────────────────────────────
    records: List[HistoryEventRow]


# Kept for backward compatibility; superseded by HistoricalLossSummary in API responses
class HistorySummary(BaseModel):
    history_loaded: bool
    history_source: str              # "template" | "user_provided" (future)
    record_count: int
    years_covered: List[int]
    calibration_active: bool
    calibration_source: str          # "historical_loss_records" | "none"
    calibrated_parameters: Dict[str, float]
    records: List[HistoryEventRow]


class PoolingMemberStats(BaseModel):
    member_id: int
    label: str
    expected_annual_loss: float
    allocation_weight: float
    standalone_cv: float
    pooled_cv: float
    allocated_ri_premium_annual: float
    allocated_scr: float
    allocated_5yr_tcor: float


class PoolingResult(BaseModel):
    enabled: bool
    n_members: int
    # ── Pool diversification ──────────────────────────────────────────────────
    pooled_mean_annual_loss: float
    pooled_cv: float
    pooled_var_995: float
    standalone_cv: float
    standalone_var_995: float
    cv_reduction_pct: float
    var_reduction_pct: float
    # ── Economics ─────────────────────────────────────────────────────────────
    pooled_ri_premium_annual: float
    standalone_ri_premium_annual: float
    ri_premium_reduction_pct: float
    pooled_scr: float
    standalone_scr: float
    scr_reduction_pct: float
    # ── TCOR comparison ───────────────────────────────────────────────────────
    operator_5yr_tcor_standalone: float
    operator_5yr_tcor_pooled: float
    tcor_improvement_pct: float
    # ── Member breakdown ──────────────────────────────────────────────────────
    members: List[PoolingMemberStats]
    # ── Verdict ───────────────────────────────────────────────────────────────
    viable: bool
    verdict_narrative: str
    known_simplifications: List[str] = Field(default_factory=list)


class FeasibilityResponse(BaseModel):
    baseline: ScenarioBlock
    mitigated: Optional[ScenarioBlock] = None
    comparison: Optional[ComparisonBlock] = None
    report: ReportBlock
    metadata: MetadataBlock
    allocation: Optional[AllocationSummary] = None
    history: Optional[HistoricalLossSummary] = None
    pooling: Optional[PoolingResult] = None


# ─────────────────────────────────────────────────────────────────────────────
# Mitigation library response
# ─────────────────────────────────────────────────────────────────────────────

class MitigationActionInfo(BaseModel):
    id: str
    name: str
    description: str
    affected_domains: List[str]
    probability_reduction: float
    severity_reduction: float
    annual_cost_nok: float
    capex_nok: float
    targeted_risk_types: List[str]

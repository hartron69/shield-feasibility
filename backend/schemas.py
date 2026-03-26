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
    sites: Optional[List["SiteProfileInput"]] = None


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
    composite_score_delta: float = 0.0   # points gained (positive = improvement)
    # Per-criterion breakdown: [{name, baseline_raw, mitigated_raw, delta_weighted}]
    criterion_deltas: List[Dict] = Field(default_factory=list)
    mitigation_score_note: str = ""      # plain-language explanation of score change


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

    # ── Self-handled vs reported split (smolt internal calibration) ──────────
    reported_total_nok: float = 0.0       # losses reported to insurer (loss ratio)
    self_handled_total_nok: float = 0.0   # losses below deductible (MC calibration only)
    domain_frequencies: Dict[str, float] = Field(default_factory=dict)  # domain → events/yr

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


# ─────────────────────────────────────────────────────────────────────────────
# Loss Analysis response models (Tapsanalyse tab)
# ─────────────────────────────────────────────────────────────────────────────

class LossAnalysisSite(BaseModel):
    site_id: str
    site_name: str
    expected_annual_loss_nok: float
    var95_nok: float = 0.0
    scr_contribution_nok: float = 0.0
    scr_share_pct: float = 0.0
    dominant_domain: str = "biological"
    domain_breakdown: Dict[str, float] = Field(default_factory=dict)


class LossAnalysisMitigatedSite(BaseModel):
    site_id: str
    site_name: str
    expected_annual_loss_nok: float
    dominant_domain: str = "biological"
    domain_breakdown: Dict[str, float] = Field(default_factory=dict)


class LossAnalysisMitigated(BaseModel):
    per_site: List[LossAnalysisMitigatedSite] = Field(default_factory=list)
    per_domain: Dict[str, float] = Field(default_factory=dict)
    delta_total_eal_nok: float = 0.0
    delta_total_scr_nok: float = 0.0


class LossAnalysisDriver(BaseModel):
    label: str
    risk_type: str = ""
    domain: str
    impact_nok: float
    impact_share_pct: float = 0.0


class LossAnalysisBlock(BaseModel):
    per_site: List[LossAnalysisSite] = Field(default_factory=list)
    per_domain: Dict[str, float] = Field(default_factory=dict)
    top_drivers: List[LossAnalysisDriver] = Field(default_factory=list)
    mitigated: Optional[LossAnalysisMitigated] = None
    method_note: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Traceability block (C5AI+ → Feasibility data lineage)
# ─────────────────────────────────────────────────────────────────────────────

class TraceabilitySiteTrace(BaseModel):
    site_id: str
    site_name: str
    eal_nok: float = 0.0
    scr_contribution_nok: float = 0.0
    top_domains: List[str] = Field(default_factory=list)
    locality_no: Optional[int] = None


class TraceabilityBlock(BaseModel):
    analysis_id: str = ""
    generated_at: str = ""
    source: str = "static_model"        # "static_model" | "c5ai_plus" | "c5ai_plus_mitigated"
    c5ai_enriched: bool = False
    c5ai_scale_factor: Optional[float] = None
    site_count: int = 0
    domain_count: int = 0
    risk_type_count: int = 0
    site_ids: List[str] = Field(default_factory=list)
    domains_used: List[str] = Field(default_factory=list)
    risk_types_used: List[str] = Field(default_factory=list)
    data_mode: str = "static_model"     # "static_model" | "c5ai_forecast" | "c5ai_forecast_mitigated"
    mitigated_forecast_used: bool = False
    applied_mitigations: List[str] = Field(default_factory=list)
    mapping_note: str = ""
    site_trace: List[TraceabilitySiteTrace] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# C5AI+ gate / freshness response models
# ─────────────────────────────────────────────────────────────────────────────

class C5AIRunResponse(BaseModel):
    run_id: str
    generated_at: str
    status: str = "ok"          # "ok" | "stub"
    site_count: int = 0
    domain_count: int = 4
    risk_type_count: int = 0
    pipeline_ran: bool = False
    message: str = ""
    freshness: str = "fresh"    # "fresh" | "stale" | "missing"


class C5AIStatusResponse(BaseModel):
    run_id: Optional[str] = None
    c5ai_last_run_at: Optional[str] = None
    inputs_last_updated_at: Optional[str] = None
    is_fresh: bool = False
    freshness: str = "missing"  # "fresh" | "stale" | "missing"


class C5AISiteTrace(BaseModel):
    site_id: str
    site_name: str
    expected_annual_loss_nok: float = 0.0
    scr_contribution_nok: float = 0.0
    dominant_domain: str = ""
    top_risk_types: List[str] = Field(default_factory=list)
    # Transparency fields — populated by _build_c5ai_meta()
    # domain_sources: per-domain source label ("c5ai_plus" | "estimated")
    domain_sources: Dict[str, str] = Field(default_factory=dict)
    # confidence_score: 0.0–1.0 heuristic reflecting data quality for this site
    confidence_score: float = 0.0
    # confidence_label: human-readable summary in Norwegian
    confidence_label: str = "Lav"
    locality_no: Optional[int] = None


class C5AIRunMeta(BaseModel):
    """Snapshot of C5AI+ run state attached to each FeasibilityResponse."""
    run_id: Optional[str] = None
    generated_at: Optional[str] = None
    is_fresh: bool = False
    freshness: str = "missing"  # "fresh" | "stale" | "missing"
    site_count: int = 0
    site_ids: List[str] = Field(default_factory=list)
    site_names: List[str] = Field(default_factory=list)
    data_mode: str = "simulated"
    domains_used: List[str] = Field(default_factory=list)
    risk_type_count: int = 0
    source_labels: List[str] = Field(default_factory=list)
    site_trace: List[C5AISiteTrace] = Field(default_factory=list)
    # Scale factor from ForecastPipeline (<1.0 = lower bio risk than static model)
    c5ai_vs_static_ratio: Optional[float] = None


class FeasibilityResponse(BaseModel):
    baseline: ScenarioBlock
    mitigated: Optional[ScenarioBlock] = None
    comparison: Optional[ComparisonBlock] = None
    report: ReportBlock
    metadata: MetadataBlock
    allocation: Optional[AllocationSummary] = None
    history: Optional[HistoricalLossSummary] = None
    pooling: Optional[PoolingResult] = None
    loss_analysis: Optional[LossAnalysisBlock] = None
    traceability: Optional[TraceabilityBlock] = None
    c5ai_meta: Optional[C5AIRunMeta] = None


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
    facility_type: str = "sea"


class SiteProfileInput(BaseModel):
    site_id: str
    site_name: str
    biomass_value_nok: float = Field(gt=0)
    fjord_exposure: str = "semi_exposed"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    municipality: Optional[str] = None
    licence_count: int = 1
    lice_pressure_factor: float = Field(default=1.0, ge=0.1, le=5.0)
    hab_risk_factor: float = Field(default=1.0, ge=0.1, le=5.0)
    mooring_age_years: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# Settefisk (smolt) request models — Sprint S1
# ─────────────────────────────────────────────────────────────────────────────

class BuildingComponentInput(BaseModel):
    name: str
    area_sqm: float = Field(gt=0)
    value_per_sqm_nok: float = Field(default=27_000, gt=0)
    notes: Optional[str] = None


class SmoltFacilityInput(BaseModel):
    facility_name: str
    facility_type: str = "smolt_ras"   # smolt_ras | smolt_flow | smolt_hybrid
    building_components: List[BuildingComponentInput] = Field(default_factory=list)
    site_clearance_nok: float = Field(default=0.0, ge=0)
    machinery_nok: float = Field(default=0.0, ge=0)
    avg_biomass_insured_value_nok: float = Field(default=0.0, ge=0)
    bi_sum_insured_nok: float = Field(default=0.0, ge=0)
    bi_indemnity_months: int = Field(default=24, ge=6, le=36)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    municipality: Optional[str] = None


class SmoltOperatorRequest(BaseModel):
    """Top-level request for smolt analysis. Sent to POST /api/feasibility/smolt/run."""
    operator_name: str
    org_number: Optional[str] = None
    facilities: List[SmoltFacilityInput] = Field(min_length=1)

    # Financials
    annual_revenue_nok: Optional[float] = Field(default=None, gt=0)
    ebitda_nok: Optional[float] = None
    equity_nok: Optional[float] = None
    operating_cf_nok: Optional[float] = None
    liquidity_nok: Optional[float] = None

    # Claims history
    claims_history_years: int = Field(default=0, ge=0)
    total_claims_paid_nok: float = Field(default=0.0, ge=0)

    # Current insurance
    current_market_premium_nok: Optional[float] = None
    current_insurer: Optional[str] = None
    current_bi_indemnity_months: Optional[int] = None

    # Tiltak (mitigations) — optional; same structure as sea-based route
    mitigation: Optional[MitigationInput] = None

    # Detailed loss history (self-handled internal records, not reported to insurer)
    historical_losses: Optional[List[dict]] = Field(default=None)
    loss_calibration_note: Optional[str] = None

    # Model settings (reuses existing schema)
    model: ModelSettingsInput = Field(default_factory=ModelSettingsInput)
    generate_pdf: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Scenario request / response — Sprint S6
# ─────────────────────────────────────────────────────────────────────────────

class ScenarioRequest(BaseModel):
    facility_type: str = "sea"
    preset_id: Optional[str] = None
    operator: Optional[OperatorProfileInput] = None
    smolt_operator: Optional[SmoltOperatorRequest] = None
    # Sea parameters (from existing sliders)
    total_biomass_override: Optional[float] = None
    dissolved_oxygen_mg_l: Optional[float] = None
    nitrate_umol_l: Optional[float] = None
    lice_pressure_index: Optional[float] = None
    exposure_factor: Optional[float] = None
    operational_factor: Optional[float] = None
    # Smolt / RAS parameters (new)
    ras_failure_multiplier: Optional[float] = None
    power_backup_hours: Optional[float] = None
    oxygen_level_mg_l: Optional[float] = None
    affected_facility_index: Optional[int] = None


class ScenarioFacilityResultResponse(BaseModel):
    facility_name: str
    baseline_expected_loss: float
    scenario_expected_loss: float
    change_pct: float
    var_99_5_baseline: float
    var_99_5_scenario: float
    highest_risk_driver: str
    loss_by_category: Dict[str, float]


class ScenarioResponse(BaseModel):
    preset_id: str
    facility_type: str
    baseline_total_loss: float
    scenario_total_loss: float
    total_change_pct: float
    facility_results: List[ScenarioFacilityResultResponse]
    highest_risk_driver: str
    narrative: str

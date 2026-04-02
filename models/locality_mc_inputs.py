"""
models/locality_mc_inputs.py

Translates a LocalityRiskProfile into an OperatorInput ready for the existing
MonteCarloEngine.  No new simulation engine is introduced — this module is a
bridge between the Sprint 1 risk profile layer and the existing compound
Poisson-LogNormal engine.

Frequency / severity mapping
-----------------------------
total_risk_score drives the overall level via sigmoid multipliers.
domain_multipliers split the effect by domain character:

  Frequency   biological  0.60 | environmental  0.25 | operational  0.15
  Severity    structural  0.60 | operational    0.25 | biological   0.15

Domain weights (from domain_weights) drive the non-bio fraction split that
is passed to MonteCarloEngine.non_bio_domain_fracs → build_domain_loss_breakdown.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

from data.input_schema import (
    CurrentInsuranceProgram,
    FinancialProfile,
    HistoricalLossRecord,
    OperatorInput,
    RiskParameters,
    SiteProfile,
)
from models.locality_risk_profile import LocalityRiskProfile

# ── Constants ───────────────────────────────────────────────────────────────────

_BIOMASS_VALUE_PER_TONNE_NOK: float = 65_000
_REVENUE_FACTOR:   float = 1.20   # annual revenue = biomass_value × 1.20
_EQUIPMENT_FACTOR: float = 0.10   # equipment = biomass_value × 0.10
_INFRA_FACTOR:     float = 0.07   # infrastructure = biomass_value × 0.07

# Matches SeaSiteBuilder constants
_CV_LOSS_SEVERITY:        float = 0.85
_CAT_PROBABILITY:         float = 0.05
_CAT_MULTIPLIER:          float = 3.5
_BI_TRIGGER_THRESHOLD:    float = 0.30
_BI_INTERRUPTION_DAYS:    float = 30.0

# Domain frequency split  (must sum to 1.0)
_FREQ_DOMAIN_WEIGHTS: Dict[str, float] = {
    "biological":    0.60,
    "environmental": 0.25,
    "operational":   0.15,
}

# Domain severity split  (must sum to 1.0)
_SEV_DOMAIN_WEIGHTS: Dict[str, float] = {
    "structural":  0.60,
    "operational": 0.25,
    "biological":  0.15,
}


# ── Sigmoid helpers ─────────────────────────────────────────────────────────────

def score_to_frequency_multiplier(
    score: float,
    low: float = 0.40,
    high: float = 1.60,
    mid: float = 50.0,
    steepness: float = 0.08,
) -> float:
    """
    Map total_risk_score [0–100] to a frequency multiplier via sigmoid.

    Calibrated so that score=50 yields exactly 1.0 (neutral baseline).
    Range: ~0.50 at score 20  →  ~1.50 at score 80.
    """
    x = 1.0 / (1.0 + math.exp(-steepness * (score - mid)))
    return low + (high - low) * x


def score_to_severity_multiplier(
    score: float,
    low: float = 0.70,
    high: float = 1.30,
    mid: float = 50.0,
    steepness: float = 0.06,
) -> float:
    """
    Map total_risk_score [0–100] to a severity multiplier via sigmoid.

    Intentionally milder than frequency: score=50 → 1.0, range ~0.76–1.24.
    Severity is more structural than signal-driven.
    """
    x = 1.0 / (1.0 + math.exp(-steepness * (score - mid)))
    return low + (high - low) * x


# ── Data model ──────────────────────────────────────────────────────────────────

@dataclass
class LocalityMonteCarloInput:
    """
    Intermediate container holding the OperatorInput built from a
    LocalityRiskProfile, plus the transparency fields used in tests and the API.

    operator_input and cage_multipliers / non_bio_domain_fracs are passed
    directly to MonteCarloEngine.
    """

    locality_id: str

    # -- Transparency fields (for tests and API response)
    base_expected_events:   float   # from SiteProfile.base_loss_frequency
    base_mean_severity_nok: float   # from SiteProfile.base_severity_nok
    frequency_multiplier:   float   # score_to_frequency_multiplier(total_risk_score)
    severity_multiplier:    float   # score_to_severity_multiplier(total_risk_score)
    domain_freq_factor:     float   # weighted blend of bio/env/ops domain_multipliers
    domain_sev_factor:      float   # weighted blend of struct/ops/bio domain_multipliers
    effective_expected_events:   float
    effective_mean_severity_nok: float

    # -- Ready for MonteCarloEngine
    operator_input:      OperatorInput
    cage_multipliers:    Dict[str, float]   # passed as cage_multipliers to engine
    non_bio_domain_fracs: Dict[str, float]  # passed as non_bio_domain_fracs to engine


# ── Builder ─────────────────────────────────────────────────────────────────────

def build_locality_mc_inputs(profile: LocalityRiskProfile) -> LocalityMonteCarloInput:
    """
    Translate a LocalityRiskProfile into a LocalityMonteCarloInput.

    The returned operator_input can be fed directly to MonteCarloEngine.
    Use cage_multipliers and non_bio_domain_fracs as the corresponding
    engine keyword arguments.
    """

    # ── 1. Construct a SiteProfile to obtain canonical base frequency/severity ─
    site = _profile_to_site_profile(profile)
    base_freq = site.base_loss_frequency   # exposure-driven annual frequency
    base_sev  = site.base_severity_nok     # 18% of biomass value

    # ── 2. Score-level multipliers (sigmoid) ──────────────────────────────────
    freq_mult = score_to_frequency_multiplier(profile.total_risk_score)
    sev_mult  = score_to_severity_multiplier(profile.total_risk_score)

    # ── 3. Domain multiplier blends ───────────────────────────────────────────
    dm = profile.domain_multipliers
    bio_m    = dm.get("biological",    1.0)
    struct_m = dm.get("structural",    1.0)
    env_m    = dm.get("environmental", 1.0)
    ops_m    = dm.get("operational",   1.0)

    domain_freq_factor = (
        bio_m  * _FREQ_DOMAIN_WEIGHTS["biological"] +
        env_m  * _FREQ_DOMAIN_WEIGHTS["environmental"] +
        ops_m  * _FREQ_DOMAIN_WEIGHTS["operational"]
    )
    domain_sev_factor = (
        struct_m * _SEV_DOMAIN_WEIGHTS["structural"] +
        ops_m    * _SEV_DOMAIN_WEIGHTS["operational"] +
        bio_m    * _SEV_DOMAIN_WEIGHTS["biological"]
    )

    # ── 4. Effective simulation parameters ────────────────────────────────────
    effective_events = base_freq * freq_mult * domain_freq_factor
    effective_sev    = base_sev  * sev_mult  * domain_sev_factor

    # ── 5. Non-bio domain fracs from domain_weights ────────────────────────────
    dw = profile.domain_weights
    non_bio_total = dw.structural + dw.environmental + dw.operational
    if non_bio_total > 1e-9:
        non_bio_fracs: Dict[str, float] = {
            "structural":    dw.structural    / non_bio_total,
            "environmental": dw.environmental / non_bio_total,
            "operational":   dw.operational   / non_bio_total,
        }
    else:
        non_bio_fracs = {"structural": 0.50, "environmental": 0.25, "operational": 0.25}

    # ── 6. Build full OperatorInput ───────────────────────────────────────────
    annual_revenue = profile.biomass_value_nok * _REVENUE_FACTOR
    operator_input = _build_operator_input(
        profile=profile,
        site=site,
        effective_events=effective_events,
        effective_sev=effective_sev,
        annual_revenue=annual_revenue,
    )

    return LocalityMonteCarloInput(
        locality_id=profile.locality_id,
        base_expected_events=base_freq,
        base_mean_severity_nok=base_sev,
        frequency_multiplier=freq_mult,
        severity_multiplier=sev_mult,
        domain_freq_factor=domain_freq_factor,
        domain_sev_factor=domain_sev_factor,
        effective_expected_events=effective_events,
        effective_mean_severity_nok=effective_sev,
        operator_input=operator_input,
        cage_multipliers=dict(dm),
        non_bio_domain_fracs=non_bio_fracs,
    )


# ── Private helpers ─────────────────────────────────────────────────────────────

def _exposure_class(factor: float) -> str:
    if factor >= 1.12:
        return "open_coast"
    if factor >= 1.0:
        return "semi_exposed"
    return "sheltered"


def _profile_to_site_profile(profile: LocalityRiskProfile) -> SiteProfile:
    """Build a minimal SiteProfile from a LocalityRiskProfile.

    lice_pressure_factor and hab_risk_factor are set to 1.0 — the live risk
    score already integrates these signals; we don't want to double-count.
    """
    return SiteProfile(
        name=profile.locality_name,
        location=profile.region,
        species="Atlantic Salmon",
        biomass_tonnes=profile.biomass_tonnes,
        biomass_value_per_tonne=_BIOMASS_VALUE_PER_TONNE_NOK,
        equipment_value=profile.biomass_value_nok * _EQUIPMENT_FACTOR,
        infrastructure_value=profile.biomass_value_nok * _INFRA_FACTOR,
        annual_revenue=profile.biomass_value_nok * _REVENUE_FACTOR,
        fjord_exposure=_exposure_class(profile.exposure_factor),
        lice_pressure_factor=1.0,
        hab_risk_factor=1.0,
    )


def _build_operator_input(
    profile: LocalityRiskProfile,
    site: SiteProfile,
    effective_events: float,
    effective_sev: float,
    annual_revenue: float,
) -> OperatorInput:
    """Construct a minimal but valid OperatorInput for MonteCarloEngine."""
    biomass_value = profile.biomass_value_nok

    insurance = CurrentInsuranceProgram(
        annual_premium=annual_revenue * 0.020,
        per_occurrence_deductible=annual_revenue * 0.005,
        annual_aggregate_deductible=0.0,
        coverage_limit=biomass_value,
        aggregate_limit=biomass_value * 1.5,
        coverage_lines=["Mortality", "Property"],
        insurer_names=["Market"],
        current_loss_ratio=0.65,
        market_rating_trend=0.03,
    )

    financials = FinancialProfile(
        annual_revenue=annual_revenue,
        ebitda=annual_revenue * 0.18,
        total_assets=biomass_value * 1.5,
        net_equity=biomass_value * 0.40,
        credit_rating=None,
        free_cash_flow=annual_revenue * 0.08,
        years_in_operation=5,
    )

    risk_params = RiskParameters(
        expected_annual_events=effective_events,
        mean_loss_severity=effective_sev,
        cv_loss_severity=_CV_LOSS_SEVERITY,
        catastrophe_probability=_CAT_PROBABILITY,
        catastrophe_loss_multiplier=_CAT_MULTIPLIER,
        inter_site_correlation=0.0,            # single-locality run
        bi_trigger_threshold=_BI_TRIGGER_THRESHOLD,
        bi_daily_revenue_loss=annual_revenue / 365.0,
        bi_average_interruption_days=_BI_INTERRUPTION_DAYS,
    )

    return OperatorInput(
        name=profile.company_name,
        registration_number=profile.locality_id,
        country="Norway",
        reporting_currency="NOK",
        sites=[site],
        current_insurance=insurance,
        historical_losses=[],
        financials=financials,
        risk_params=risk_params,
        facility_type="sea_based",
    )

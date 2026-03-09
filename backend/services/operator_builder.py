"""
Convert simplified GUI input (OperatorProfileInput) into a full OperatorInput
by overlaying on the sample_input.json template.

Scaling rules (Phase 1)
-----------------------
Risk parameters
  mean_loss_severity  scales with biomass exposure (tiv_ratio = user / template)
  expected_annual_events  scales with sqrt(n_sites / template_n_sites)
  cv, catastrophe params, inter_site_correlation  unchanged (operator-independent)

Financial ratios derived from template (template revenue = NOK 897 M):
  ebitda_margin  = 191 / 897 = 21.3 %
  equity_ratio   = 567 / 897 = 63.2 %
  fcf_ratio      = 103 / 897 = 11.5 %
  assets_ratio   = 1176 / 897 = 131.1 %

Equipment / infrastructure (bug fix)
  The old code multiplied by n / base_n, causing TIV inflation as site count grew.
  Now: total_equipment = user_exposure × (template_equipment / template_exposure)
  Distributed by per-site biomass weight — no n-scaling multiplier.

Site cloning (Phase 2)
  When n_sites > len(template_sites): clone only *farm* sites (site_type="production"),
  not the processing facility ("Sunnfjord Prosessering").  Generated sites are named
  "Generert Lokalitet N" to distinguish them from template sites.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import List, Optional, Tuple

from backend.schemas import (
    AllocationSummary,
    BiomassValuationSummary,
    OperatorProfileInput,
    SiteAllocationRow,
)
from data.input_schema import OperatorInput, validate_input


_SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_input.json"

# ── Template constants (derived from data/sample_input.json) ──────────────────
# Biomass exposure
_TEMPLATE_BIOMASS_TOTAL = 9_200           # tonnes (4200 + 3800 + 1200)
_TEMPLATE_BIOMASS_VALUE = 72_000          # NOK/tonne
_TEMPLATE_EXPOSURE = _TEMPLATE_BIOMASS_TOTAL * _TEMPLATE_BIOMASS_VALUE  # 662 400 000

# Equipment / infrastructure totals
_TEMPLATE_EQUIPMENT_TOTAL = 37_000_000 + 30_500_000 + 44_000_000   # 111 500 000
_TEMPLATE_INFRA_TOTAL = 29_000_000 + 25_000_000 + 59_000_000        # 113 000 000
_TEMPLATE_EQUIP_RATIO = _TEMPLATE_EQUIPMENT_TOTAL / _TEMPLATE_EXPOSURE
_TEMPLATE_INFRA_RATIO = _TEMPLATE_INFRA_TOTAL / _TEMPLATE_EXPOSURE

# Risk parameters
_TEMPLATE_N_SITES = 3
_TEMPLATE_EVENTS = 2.8
_TEMPLATE_SEVERITY = 7_100_000

# Financial ratios relative to annual_revenue
_TEMPLATE_REVENUE = 897_000_000
_EBITDA_MARGIN = 191_000_000 / _TEMPLATE_REVENUE   # 0.2130
_EQUITY_RATIO = 567_000_000 / _TEMPLATE_REVENUE    # 0.6321
_FCF_RATIO = 103_000_000 / _TEMPLATE_REVENUE       # 0.1148
_ASSETS_RATIO = 1_176_000_000 / _TEMPLATE_REVENUE  # 1.3111


def _load_template() -> dict:
    with open(_SAMPLE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


_MIN_HISTORY_RECORDS = 3   # minimum records required for calibration


def build_operator_input(
    profile: OperatorProfileInput,
    use_history_calibration: bool = False,
) -> Tuple[OperatorInput, AllocationSummary]:
    """
    Build a full OperatorInput from a simplified GUI profile.

    Parameters
    ----------
    profile:
        Simplified GUI inputs.
    use_history_calibration:
        When True and the template contains ≥3 historical loss records,
        derive mean_loss_severity and expected_annual_events from the observed
        data instead of TIV-ratio scaling.

    Returns
    -------
    (OperatorInput, AllocationSummary)
        The fully-validated operator data and a transparency summary of how
        each value was derived / scaled (or calibrated) from the template.
    """
    tmpl = _load_template()
    raw_hist: List[dict] = tmpl.get("historical_losses", [])
    warnings: List[str] = []

    # ── Top-level overrides ───────────────────────────────────────────────────
    tmpl["name"] = profile.name
    tmpl["country"] = profile.country
    tmpl["current_insurance"]["annual_premium"] = profile.annual_premium_nok

    # ── Biomass valuation ─────────────────────────────────────────────────────
    # suggested = reference_price_per_kg × 1000 × realisation_factor × (1 - prudence_haircut)
    suggested_value = (
        profile.reference_price_per_kg
        * 1000
        * profile.realisation_factor
        * (1.0 - profile.prudence_haircut)
    )
    if profile.biomass_value_per_tonne_override is not None:
        if profile.biomass_value_per_tonne_override <= 0:
            raise ValueError("biomass_value_per_tonne_override must be positive")
        applied_value = profile.biomass_value_per_tonne_override
        user_overridden = True
    else:
        applied_value = profile.biomass_value_per_tonne   # backward-compat: use submitted field
        user_overridden = False

    biomass_valuation = BiomassValuationSummary(
        reference_price_per_kg=profile.reference_price_per_kg,
        realisation_factor=profile.realisation_factor,
        prudence_haircut=profile.prudence_haircut,
        suggested_biomass_value_per_tonne=round(suggested_value, 2),
        applied_biomass_value_per_tonne=float(applied_value),
        user_overridden=user_overridden,
    )

    # ── Exposure ratio ────────────────────────────────────────────────────────
    user_exposure = profile.total_biomass_tonnes * applied_value
    tiv_ratio = user_exposure / _TEMPLATE_EXPOSURE

    # ── Risk parameter scaling ────────────────────────────────────────────────
    mean_severity = round(_TEMPLATE_SEVERITY * tiv_ratio)
    expected_events = round(_TEMPLATE_EVENTS * math.sqrt(profile.n_sites / _TEMPLATE_N_SITES), 4)

    # ── History calibration (overrides TIV scaling when requested) ────────────
    calibration_active = False
    calibrated_parameters: dict = {}
    calibration_mode = "none"
    if use_history_calibration and len(raw_hist) >= _MIN_HISTORY_RECORDS:
        hist_severities = [r["gross_loss"] for r in raw_hist]
        hist_n_years = len(set(r["year"] for r in raw_hist))
        cal_severity = round(sum(hist_severities) / len(hist_severities))
        cal_events = round(len(raw_hist) / hist_n_years, 4)
        mean_severity = cal_severity
        expected_events = cal_events
        calibrated_parameters = {
            "mean_loss_severity": float(cal_severity),
            "expected_annual_events": float(cal_events),
        }
        calibration_active = True
        calibration_mode = "portfolio"

    tmpl["risk_params"]["mean_loss_severity"] = mean_severity
    tmpl["risk_params"]["expected_annual_events"] = expected_events
    # cv, cat_prob, cat_mult, correlation unchanged — operator-independent

    # ── Financial scaling ─────────────────────────────────────────────────────
    revenue = profile.annual_revenue_nok
    tmpl["financials"]["annual_revenue"] = revenue
    tmpl["financials"]["ebitda"] = round(revenue * _EBITDA_MARGIN)
    tmpl["financials"]["net_equity"] = round(revenue * _EQUITY_RATIO)
    tmpl["financials"]["free_cash_flow"] = round(revenue * _FCF_RATIO)
    tmpl["financials"]["total_assets"] = round(revenue * _ASSETS_RATIO)

    # ── Site list construction ────────────────────────────────────────────────
    n = profile.n_sites
    base_sites = tmpl["sites"]

    # Farm sites only (site_type != "processing") — used when we need to clone
    farm_sites = [s for s in base_sites if s.get("site_type", "production") != "processing"]
    if not farm_sites:
        farm_sites = base_sites  # fallback: use all if no type info

    if n <= len(base_sites):
        target_sites = copy.deepcopy(base_sites[:n])
    else:
        # Start from all template sites, then append generated farm sites
        target_sites = copy.deepcopy(base_sites)
        for i in range(n - len(base_sites)):
            clone = copy.deepcopy(farm_sites[i % len(farm_sites)])
            clone["name"] = f"Generert Lokalitet {i + 1}"
            clone["site_type"] = "production"
            target_sites.append(clone)

    # Pre-compute template biomass weights (before overwriting biomass values)
    total_template_biomass = sum(s["biomass_tonnes"] for s in target_sites)
    if total_template_biomass == 0:
        total_template_biomass = len(target_sites)

    # User-level equipment/infrastructure totals (no n-scaling multiplier)
    total_equipment_user = user_exposure * _TEMPLATE_EQUIP_RATIO
    total_infra_user = user_exposure * _TEMPLATE_INFRA_RATIO

    site_rows: List[SiteAllocationRow] = []
    for site in target_sites:
        weight = site["biomass_tonnes"] / total_template_biomass
        biomass_t = round(profile.total_biomass_tonnes * weight)
        revenue_s = round(revenue * weight)
        equip_s = round(total_equipment_user * weight)
        infra_s = round(total_infra_user * weight)
        tiv_s = biomass_t * profile.biomass_value_per_tonne + equip_s + infra_s

        site["biomass_tonnes"] = biomass_t
        site["biomass_value_per_tonne"] = applied_value
        site["annual_revenue"] = revenue_s
        site["equipment_value"] = equip_s
        site["infrastructure_value"] = infra_s

        site_rows.append(SiteAllocationRow(
            name=site["name"],
            biomass_tonnes=biomass_t,
            biomass_value_nok=float(biomass_t * applied_value),
            equipment_value_nok=float(equip_s),
            infrastructure_value_nok=float(infra_s),
            annual_revenue_nok=float(revenue_s),
            tiv_nok=float(tiv_s),
            weight_pct=round(weight * 100, 1),
        ))

    tmpl["sites"] = target_sites

    # ── Allocation sanity checks ───────────────────────────────────────────────
    actual_biomass = sum(s["biomass_tonnes"] for s in target_sites)
    if abs(actual_biomass - profile.total_biomass_tonnes) > 50:
        warnings.append(
            f"Biomass rounding drift: allocated {actual_biomass:,} t vs "
            f"requested {int(profile.total_biomass_tonnes):,} t"
        )

    actual_revenue = sum(s["annual_revenue"] for s in target_sites)
    if actual_revenue > 0 and abs(actual_revenue - revenue) / revenue > 0.01:
        warnings.append(
            f"Revenue rounding drift: allocated NOK {actual_revenue / 1e6:.1f} M "
            f"vs requested NOK {revenue / 1e6:.1f} M"
        )

    premium_to_revenue = profile.annual_premium_nok / revenue
    if premium_to_revenue > 0.05:
        warnings.append(
            f"Premium/revenue ratio is {premium_to_revenue:.1%} — "
            f"unusually high (typical aquaculture: 1.5–3.0 %)"
        )

    # ── Build operator and allocation summary ──────────────────────────────────
    operator = validate_input(tmpl)

    allocation = AllocationSummary(
        template_exposure_nok=float(_TEMPLATE_EXPOSURE),
        user_exposure_nok=float(user_exposure),
        tiv_ratio=round(tiv_ratio, 4),
        risk_severity_scaled=float(mean_severity),
        risk_events_scaled=float(expected_events),
        financial_ratios={
            "ebitda_margin": round(_EBITDA_MARGIN, 4),
            "equity_ratio": round(_EQUITY_RATIO, 4),
            "fcf_ratio": round(_FCF_RATIO, 4),
            "assets_ratio": round(_ASSETS_RATIO, 4),
        },
        sites=site_rows,
        biomass_valuation=biomass_valuation,
        calibration_active=calibration_active,
        calibration_mode=calibration_mode,
        calibrated_parameters=calibrated_parameters,
        warnings=warnings,
    )

    return operator, allocation


def load_template_history() -> List[dict]:
    """Return the historical_losses list from the template JSON."""
    return _load_template().get("historical_losses", [])

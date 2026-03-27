"""
backend/services/live_risk_economics.py

Translates locality risk score deltas into financial impact estimates:
  - Expected Loss (EL) — current annual and period delta
  - Solvency Capital Requirement (SCR) — current and delta
  - Indicative premium — current annual and period delta
  - Per-domain EL attribution
  - Per-cage EL attribution (proportional biomass split)

Methodology is fully config-driven; see config/live_risk_economics.py.
This is a linear approximation — not a full actuarial pricing engine.
"""
from __future__ import annotations

from backend.services.live_risk_mock import (
    get_locality_data,
    slice_by_period,
    DAYS,
)
from backend.services.risk_change_explainer import get_change_breakdown
from config.live_risk_economics import (
    BASE_EL_RATE_AT_REF,
    REFERENCE_RISK_SCORE,
    EL_ELASTICITY_PER_POINT,
    DOMAIN_WEIGHTS,
    SCR_LOADING,
    PREMIUM_LOADING,
    LOCALITY_FINANCIALS,
)

_DOMAINS = ["biological", "structural", "environmental", "operational"]


def _mean(vals: list, default: float = 0.0) -> float:
    non_null = [v for v in vals if v is not None]
    return sum(non_null) / len(non_null) if non_null else default


def get_economics(locality_id: str, period: str = "30d") -> dict:
    """
    Returns financial impact estimates for the locality over the selected period.

    Steps:
      1. 7-day averaged domain risk scores at period end (current state).
      2. Risk deltas from change-breakdown service (same 7-day window logic).
      3. current_annual_EL = TIV × BASE_EL_RATE_AT_REF × (risk_score / REF_SCORE).
      4. EL_delta per domain = TIV × elasticity × domain_risk_delta × domain_weight.
      5. total_EL_delta = TIV × elasticity × total_risk_delta.
      6. SCR_delta = EL_delta × SCR_LOADING.
      7. premium_delta = EL_delta × PREMIUM_LOADING.
      8. Cage attribution: distribute locality deltas by biomass share.
    """
    if locality_id not in LOCALITY_FINANCIALS:
        raise KeyError(f"No financial profile for locality '{locality_id}'")

    fin = LOCALITY_FINANCIALS[locality_id]
    tiv_nok = fin["biomass_tonnes"] * fin["value_per_tonne_nok"]

    # Step 1 — current domain risk scores (7-day average at period end)
    data = get_locality_data(locality_id)
    risk_scores = data["risk_scores"]
    _, start_idx = slice_by_period(data["timestamps"], period)
    end_idx = DAYS - 1
    window_end = range(max(end_idx - 6, start_idx), end_idx + 1)

    domain_risk_current = {
        d: _mean([risk_scores[i][d] for i in window_end])
        for d in _DOMAINS
    }
    total_risk_current = round(
        sum(DOMAIN_WEIGHTS[d] * domain_risk_current[d] for d in _DOMAINS), 1
    )

    # Step 2 — risk deltas
    breakdown = get_change_breakdown(locality_id, period)
    domain_deltas = breakdown["domain_deltas"]
    total_delta   = breakdown["total_delta"]

    # Step 3 — current annual EL
    current_el_rate       = BASE_EL_RATE_AT_REF * (total_risk_current / REFERENCE_RISK_SCORE)
    current_annual_el_nok = round(tiv_nok * current_el_rate)

    # Step 4 — domain EL deltas (weighted contribution to total)
    domain_el_delta_nok = {
        d: round(tiv_nok * EL_ELASTICITY_PER_POINT * domain_deltas[d] * DOMAIN_WEIGHTS[d])
        for d in _DOMAINS
    }

    # Step 5 — total EL delta derived from domain sum to guarantee consistency
    # (avoids double-rounding discrepancy between domain-level and total risk delta)
    total_el_delta_nok = sum(domain_el_delta_nok.values())

    # Step 6 — SCR
    current_scr_nok = round(current_annual_el_nok * SCR_LOADING)
    scr_delta_nok   = round(total_el_delta_nok * SCR_LOADING)

    # Step 7 — premium
    current_annual_premium_nok = round(current_annual_el_nok * PREMIUM_LOADING)
    premium_delta_nok          = round(total_el_delta_nok * PREMIUM_LOADING)

    return {
        "locality_id":      locality_id,
        "period":           period,
        "tiv_nok":          tiv_nok,
        "biomass_tonnes":   fin["biomass_tonnes"],
        "value_per_tonne_nok": fin["value_per_tonne_nok"],
        # Current state
        "current_risk_score":   total_risk_current,
        "domain_risk_current":  {d: round(domain_risk_current[d], 1) for d in _DOMAINS},
        # Risk deltas for the period
        "risk_delta": {
            "total": total_delta,
            **{d: domain_deltas[d] for d in _DOMAINS},
        },
        # EL
        "current_annual_el_nok": current_annual_el_nok,
        "domain_el_delta_nok":   domain_el_delta_nok,
        "total_el_delta_nok":    total_el_delta_nok,
        # SCR
        "current_scr_nok": current_scr_nok,
        "scr_delta_nok":   scr_delta_nok,
        # Premium
        "current_annual_premium_nok": current_annual_premium_nok,
        "premium_delta_nok":          premium_delta_nok,
        # Cage attribution
        "cage_attribution": _cage_attribution(fin, total_el_delta_nok, domain_el_delta_nok),
        # Transparent methodology block
        "methodology": {
            "el_elasticity_per_point": EL_ELASTICITY_PER_POINT,
            "base_el_rate_at_ref":     BASE_EL_RATE_AT_REF,
            "reference_risk_score":    REFERENCE_RISK_SCORE,
            "scr_loading":             SCR_LOADING,
            "premium_loading":         PREMIUM_LOADING,
            "domain_weights":          DOMAIN_WEIGHTS,
            "note": (
                "Lineær EL-approksimering. EL_delta = TIV × elastisitet × risikodelta. "
                "Domenebidrag vektet etter risikoformelens domenvekter. "
                "Ikke for bruk i formell aktuarisk prising."
            ),
        },
    }


def _cage_attribution(
    fin: dict,
    total_el_delta_nok: int,
    domain_el_delta_nok: dict,
) -> list:
    """Distribute locality EL delta across pens by biomass share."""
    n_cages = fin.get("n_cages", 0)
    if n_cages == 0:
        return []

    raw_split = fin.get("cage_biomass_split")
    if raw_split and len(raw_split) == n_cages:
        total = sum(raw_split)
        weights = [s / total for s in raw_split]
    else:
        weights = [1.0 / n_cages] * n_cages

    return [
        {
            "cage_id":      f"M{i + 1:02d}",
            "biomass_share": round(w * 100, 1),
            "el_delta_nok": round(total_el_delta_nok * w),
            "domain_el_delta_nok": {
                d: round(domain_el_delta_nok[d] * w) for d in domain_el_delta_nok
            },
        }
        for i, w in enumerate(weights)
    ]

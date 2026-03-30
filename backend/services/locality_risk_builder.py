"""
backend/services/locality_risk_builder.py

Builds a LocalityRiskProfile for one or more localities by combining:
  1. Live Risk feed (domain scores, confidence, locality metadata)
  2. Cage portfolio + advanced cage weighting (when cages are supplied)
  3. Static locality config (biomass, exposure, region)

The builder never recalculates Live Risk internals — it reuses existing
service outputs to compose the unified profile object.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from backend.services.confidence_scoring import compute_confidence
from backend.services.live_risk_mock import get_locality_config, get_locality_data
from models.locality_risk_profile import (
    DOMAINS,
    LIVE_RISK_SCALE_FACTORS,
    DomainRiskScores,
    DomainRiskWeights,
    LocalityRiskProfile,
    RiskSourceSummary,
)


# ── Constants ───────────────────────────────────────────────────────────────────

_BIOMASS_VALUE_PER_TONNE_NOK = 65_000   # standard valuation (NOK/tonne)

# Thresholds for concentration flags
_HIGH_EXPOSURE_THRESHOLD    = 1.1   # exposure_factor above this → flag
_DOMAIN_DOMINANCE_THRESHOLD = 0.50  # weighted contribution share above this → flag


# ── Private helpers ─────────────────────────────────────────────────────────────

def _compute_domain_weights(scores: Dict[str, float]) -> Dict[str, float]:
    """
    Convert raw domain scores into normalized contribution fractions.

    For each domain: contribution = score × scale_factor.
    Weight = contribution / sum(all contributions).

    Returns a dict summing to 1.0 (or uniform 0.25 if all scores are zero).
    """
    contribs = {d: scores[d] * LIVE_RISK_SCALE_FACTORS[d] for d in DOMAINS}
    total = sum(contribs.values())
    if total <= 0:
        return {d: 1.0 / len(DOMAINS) for d in DOMAINS}
    return {d: round(contribs[d] / total, 4) for d in DOMAINS}


def _top_risk_drivers(weights: Dict[str, float]) -> List[str]:
    """Return domains sorted by weighted contribution, highest first."""
    return sorted(DOMAINS, key=lambda d: weights[d], reverse=True)


def _concentration_flags(
    weights: Dict[str, float],
    exposure_factor: float,
) -> List[str]:
    """Identify notable risk concentration patterns."""
    flags = []
    for domain in DOMAINS:
        if weights[domain] >= _DOMAIN_DOMINANCE_THRESHOLD:
            flags.append(f"high_{domain}_dominance")
    if exposure_factor >= _HIGH_EXPOSURE_THRESHOLD:
        flags.append("high_exposure")
    return flags


def _confidence_notes(confidence: dict) -> List[str]:
    """Extract plain-text notes from the confidence dict."""
    notes = []
    summary = confidence.get("summary")
    if summary:
        notes.append(summary)
    for comp in confidence.get("components", []):
        score = comp.get("score", 1.0)
        if score < 0.6:
            notes.append(comp.get("explanation", ""))
    missing = confidence.get("missing_sources", [])
    if missing:
        notes.append(f"Manglende kilder: {', '.join(missing)}")
    return [n for n in notes if n]


# ── Public API ──────────────────────────────────────────────────────────────────

def build_locality_risk_profile(
    locality_id: str,
    cages: Optional[List] = None,   # List[CagePenConfig] — from data.input_schema
) -> LocalityRiskProfile:
    """
    Build a LocalityRiskProfile for a single locality.

    Parameters
    ----------
    locality_id : str
        Must be a known locality ID (e.g. "KH_S01").
    cages : list[CagePenConfig] | None
        Optional cage portfolio. When supplied, advanced cage weighting is
        applied and domain multipliers are derived from the cage mix.
        When None, domain multipliers default to 1.0 for all domains.

    Returns
    -------
    LocalityRiskProfile
    """
    used_defaults: List[str] = []

    # ── 1. Locality config & current risk scores ─────────────────────────────
    cfg  = get_locality_config(locality_id)
    data = get_locality_data(locality_id)
    risk = data["risk_scores"][-1]          # current-day snapshot

    biomass_t = cfg.get("biomass_tonnes", 0.0)
    if not biomass_t:
        biomass_t = 0.0
        used_defaults.append("biomass_tonnes=0 (not in config)")

    biomass_value_nok = biomass_t * _BIOMASS_VALUE_PER_TONNE_NOK

    # ── 2. Confidence ────────────────────────────────────────────────────────
    confidence = compute_confidence(locality_id)

    # ── 3. Cage portfolio / advanced weighting ───────────────────────────────
    cage_count         = len(cages) if cages else 0
    cage_weighting_mode = "none"
    domain_multipliers: Dict[str, float] = {d: 1.0 for d in DOMAINS}

    if cages:
        from models.cage_weighting import compute_locality_domain_multipliers_advanced
        result = compute_locality_domain_multipliers_advanced(cages)
        cage_weighting_mode  = result.weighting_mode
        domain_multipliers   = dict(result.domain_multipliers)
    else:
        used_defaults.append("domain_multipliers=1.0 (no cage portfolio)")
        used_defaults.append("cage_weighting_mode=none")

    # ── 4. Domain scores & total ─────────────────────────────────────────────
    total_risk_score        = float(risk["total"])
    total_risk_score_source = "live_risk"
    domain_scores = DomainRiskScores(
        biological=float(risk["biological"]),
        structural=float(risk["structural"]),
        environmental=float(risk["environmental"]),
        operational=float(risk["operational"]),
    )

    # ── 5. Domain weights (normalized weighted contributions) ─────────────────
    raw_weights = _compute_domain_weights(domain_scores.to_dict())
    domain_weights = DomainRiskWeights(**raw_weights)

    # ── 6. Top drivers & concentration flags ─────────────────────────────────
    top_drivers = _top_risk_drivers(raw_weights)
    flags       = _concentration_flags(raw_weights, cfg["exposure"])

    # ── 7. Source summary ────────────────────────────────────────────────────
    # bw_live detection: try a lightweight check (no network call required —
    # get_site_profile handles this, but we avoid it here to keep the builder
    # fast; instead we check the sync_delay as a proxy for source freshness).
    bw_live = cfg.get("sync_delay_hours", 999) < 6.0   # fresh BW data → likely live

    sources_used = ["Live Risk"]
    if bw_live:
        sources_used.append("BarentsWatch")
    if cages:
        sources_used.append("Cage Portfolio")

    source_summary = RiskSourceSummary(
        live_risk_available=True,
        cage_portfolio_available=bool(cages),
        advanced_weighting_available=cage_weighting_mode == "advanced",
        bw_live=bw_live,
        sources_used=sources_used,
    )

    # ── 8. Assemble profile ──────────────────────────────────────────────────
    return LocalityRiskProfile(
        locality_id=locality_id,
        locality_name=cfg["name"],
        company_name=cfg["operator"],
        region=cfg["region"],
        drift_type="sjø",
        biomass_tonnes=biomass_t,
        biomass_value_nok=biomass_value_nok,
        exposure_factor=cfg["exposure"],
        cage_count=cage_count,
        cage_weighting_mode=cage_weighting_mode,
        total_risk_score=total_risk_score,
        total_risk_score_source=total_risk_score_source,
        domain_scores=domain_scores,
        domain_weights=domain_weights,
        domain_multipliers=domain_multipliers,
        scale_factors=dict(LIVE_RISK_SCALE_FACTORS),
        concentration_flags=flags,
        top_risk_drivers=top_drivers,
        confidence_level=confidence["overall"],
        confidence_notes=_confidence_notes(confidence),
        source_summary=source_summary,
        used_defaults=used_defaults,
        metadata={
            "locality_no":    cfg.get("locality_no"),
            "lat":            cfg.get("lat"),
            "lon":            cfg.get("lon"),
            "mtb_tonnes":     cfg.get("mtb_tonnes"),
            "exposure_class": _exposure_class(cfg["exposure"]),
            "nis_certified":  cfg.get("nis_certified", False),
            "confidence_score": confidence.get("score"),
            "data_age_hours":   confidence.get("data_age_hours"),
        },
    )


def build_locality_risk_profiles(
    locality_ids: List[str],
    cages_by_locality: Optional[Dict[str, List]] = None,
) -> List[LocalityRiskProfile]:
    """
    Build profiles for multiple localities.

    Parameters
    ----------
    locality_ids : list[str]
    cages_by_locality : dict[locality_id → list[CagePenConfig]] | None
        Optional per-locality cage portfolios.
    """
    profiles = []
    for lid in locality_ids:
        cages = (cages_by_locality or {}).get(lid)
        profiles.append(build_locality_risk_profile(lid, cages=cages))
    return profiles


# ── Internal helper ─────────────────────────────────────────────────────────────

def _exposure_class(factor: float) -> str:
    if factor >= 1.12:
        return "open_coast"
    if factor >= 1.0:
        return "semi_exposed"
    return "sheltered"

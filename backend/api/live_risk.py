"""
backend/api/live_risk.py

Live Risk Intelligence API — all endpoints under /api/live-risk/
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.services.live_risk_feed import (
    get_feed_overview,
    get_locality_detail,
    get_timeseries,
    get_risk_history,
    get_cage_impact,
    get_inputs_snapshot,
    get_pattern_signals,
    get_data_quality,
    get_site_profile,
)
from backend.services.source_health import get_source_status
from backend.services.risk_change_explainer import get_change_breakdown
from backend.services.event_timeline import get_events
from backend.services.confidence_scoring import compute_confidence
from backend.services.live_risk_economics import get_economics
from backend.services.live_risk_mock import get_all_locality_ids

router = APIRouter(prefix="/api/live-risk", tags=["live-risk"])

VALID_PERIODS = {"7d", "30d", "90d", "12m"}
_LOCALITY_IDS = set(get_all_locality_ids())


def _check_locality(locality_id: str) -> None:
    if locality_id not in _LOCALITY_IDS:
        raise HTTPException(
            status_code=404,
            detail=f"Locality '{locality_id}' not found. Valid IDs: {sorted(_LOCALITY_IDS)}",
        )


def _check_period(period: str) -> None:
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period '{period}'. Valid values: {sorted(VALID_PERIODS)}",
        )


@router.get("/feed")
def feed_overview():
    """
    Returns the live risk overview for all monitored localities.
    Includes last sync status, current risk scores, and confidence indicators.
    """
    return get_feed_overview()


@router.get("/localities/{locality_id}")
def locality_detail(locality_id: str):
    """
    Returns metadata and current risk snapshot for a single locality.
    """
    _check_locality(locality_id)
    return get_locality_detail(locality_id)


@router.get("/localities/{locality_id}/timeseries")
def locality_timeseries(
    locality_id: str,
    period: str = Query(default="30d", description="Time window: 7d, 30d, 90d, 12m"),
):
    """
    Returns raw measurement time series (lice, temperature, oxygen, salinity, treatment)
    for the requested period. Missing data points are explicitly represented as null.
    """
    _check_locality(locality_id)
    _check_period(period)
    return get_timeseries(locality_id, period)


@router.get("/localities/{locality_id}/risk-history")
def locality_risk_history(
    locality_id: str,
    period: str = Query(default="30d", description="Time window: 7d, 30d, 90d, 12m"),
):
    """
    Returns per-domain risk score history for the requested period.
    """
    _check_locality(locality_id)
    _check_period(period)
    return get_risk_history(locality_id, period)


@router.get("/localities/{locality_id}/sources")
def locality_sources(locality_id: str):
    """
    Returns per-source health status and sync metadata.
    """
    _check_locality(locality_id)
    return get_source_status(locality_id)


@router.get("/localities/{locality_id}/change-breakdown")
def locality_change_breakdown(
    locality_id: str,
    period: str = Query(default="30d", description="Time window: 7d, 30d, 90d, 12m"),
):
    """
    Returns attributable risk change breakdown explaining what drove
    risk changes over the selected period.
    """
    _check_locality(locality_id)
    _check_period(period)
    return get_change_breakdown(locality_id, period)


@router.get("/localities/{locality_id}/events")
def locality_events(
    locality_id: str,
    period: str = Query(default="30d", description="Time window: 7d, 30d, 90d, 12m"),
):
    """
    Returns risk events (threshold crossings, sync failures, spikes) for the period.
    """
    _check_locality(locality_id)
    _check_period(period)
    return get_events(locality_id, period)


@router.get("/localities/{locality_id}/confidence")
def locality_confidence(locality_id: str):
    """
    Returns confidence score and component breakdown for the locality.
    """
    _check_locality(locality_id)
    return compute_confidence(locality_id)


@router.get("/localities/{locality_id}/inputs")
def locality_inputs_snapshot(locality_id: str):
    """
    Returns per-domain input snapshots derived from the Live Risk model.
    Structural, environmental, operational, and biological readings are all
    computed from the same time-series and risk functions as the live feed —
    no separate static mock data.
    """
    _check_locality(locality_id)
    return get_inputs_snapshot(locality_id)


@router.get("/localities/{locality_id}/site-profile")
def locality_site_profile(locality_id: str):
    """
    Returns the full site profile combining Live Risk config (operator, GPS,
    exposure), BarentsWatch Akvakulturregisteret fields (MTB, species, license,
    NIS status), and operator-reported financials. Replaces MOCK_SITE_PROFILES.
    """
    _check_locality(locality_id)
    return get_site_profile(locality_id)


@router.get("/localities/{locality_id}/data-quality")
def locality_data_quality(locality_id: str):
    """
    Returns per-risk-type data quality metrics (completeness, confidence, flag,
    missing fields) derived from the Live Risk feed. Replaces static
    MOCK_DATA_QUALITY in the Inputs page.
    """
    _check_locality(locality_id)
    return get_data_quality(locality_id)


@router.get("/localities/{locality_id}/pattern-signals")
def locality_pattern_signals(locality_id: str):
    """
    Returns PatternDetector signals for the locality computed from Live Risk data.
    Covers biological (hab, lice, jellyfish, pathogen), structural, environmental,
    and operational domains. Replaces static MOCK_ALERT_SIGNALS in the Inputs page.
    """
    _check_locality(locality_id)
    return get_pattern_signals(locality_id)


@router.get("/localities/{locality_id}/cage-impact")
def locality_cage_impact(locality_id: str):
    """
    Returns indicative cage-type exposure impact based on current domain risk.
    Labeled as inferred/indicative — not stochastic per-cage attribution.
    """
    _check_locality(locality_id)
    return get_cage_impact(locality_id)


@router.get("/localities/{locality_id}/economics")
def locality_economics(
    locality_id: str,
    period: str = Query(default="30d", description="Time window: 7d, 30d, 90d, 12m"),
):
    """
    Translates the locality's risk score deltas for the selected period into
    financial impact estimates: EL delta, SCR delta, and indicative premium delta.

    Methodology is fully config-driven (config/live_risk_economics.py).
    All outputs are linear approximations — not a full actuarial pricing engine.
    Per-cage attribution is included when cage profiles are configured.
    """
    _check_locality(locality_id)
    _check_period(period)
    return get_economics(locality_id, period)

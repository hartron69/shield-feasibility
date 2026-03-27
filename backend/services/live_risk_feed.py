"""
backend/services/live_risk_feed.py

Assembles the feed overview and locality detail responses for the
Live Risk Intelligence module.
"""
from __future__ import annotations

from datetime import timedelta
from typing import List

from backend.services.live_risk_mock import (
    get_all_locality_ids,
    get_locality_config,
    get_locality_data,
    slice_by_period,
    NOW,
    DAYS,
)
from backend.services.confidence_scoring import compute_confidence
from backend.services.source_health import get_source_status


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sync_freshness(delay_h: float) -> str:
    if delay_h < 6:
        return "fresh"
    elif delay_h < 24:
        return "stale"
    elif delay_h < 72:
        return "delayed"
    else:
        return "failed"


def _dominant_domain_change(risk_scores: list, start_idx: int) -> str:
    """Return the domain with the greatest absolute change over the period."""
    domains = ["biological", "structural", "environmental", "operational"]
    start = risk_scores[start_idx]
    end = risk_scores[-1]
    deltas = {d: abs(end[d] - start[d]) for d in domains}
    return max(deltas, key=deltas.get)


def _period_start(period_days: int) -> int:
    return max(0, DAYS - period_days)


# ── Feed overview ──────────────────────────────────────────────────────────────

def get_feed_overview() -> dict:
    localities = []
    for lid in get_all_locality_ids():
        cfg = get_locality_config(lid)
        data = get_locality_data(lid)
        risk_scores = data["risk_scores"]
        confidence = compute_confidence(lid)
        source_data = get_source_status(lid)

        delay_h = cfg["sync_delay_hours"]
        freshness = _sync_freshness(delay_h)
        last_sync = (NOW - timedelta(hours=delay_h)).isoformat()

        # Risk change over last 30 days
        start_30 = _period_start(30)
        risk_now = risk_scores[-1]["total"]
        risk_30d_ago = risk_scores[start_30]["total"]
        risk_change_30d = round(risk_now - risk_30d_ago, 1)

        # Active sources
        active_sources = [s["source_name"] for s in source_data["sources"] if s["status"] == "ok"]
        new_data_points = sum(
            s["records_received"] for s in source_data["sources"] if s["status"] == "ok"
        )

        dominant_domain = _dominant_domain_change(risk_scores, start_30)

        localities.append({
            "locality_id": lid,
            "locality_name": cfg["name"],
            "locality_no": cfg["locality_no"],
            "operator": cfg["operator"],
            "region": cfg["region"],
            "lat": cfg["lat"],
            "lon": cfg["lon"],
            "last_sync": last_sync,
            "sync_freshness": freshness,
            "active_sources": active_sources,
            "new_data_points": new_data_points,
            "risk_score": round(risk_now, 1),
            "risk_change_30d": risk_change_30d,
            "dominant_domain": dominant_domain,
            "confidence": confidence["overall"],
            "confidence_score": confidence["score"],
            "has_cage_portfolio": False,  # no real cage data in live module yet
        })

    healthy = sum(1 for loc in localities if loc["sync_freshness"] == "fresh")
    warning_count = sum(1 for loc in localities if loc["sync_freshness"] in ("stale", "delayed"))
    critical_count = sum(1 for loc in localities if loc["sync_freshness"] == "failed")

    return {
        "localities": localities,
        "last_updated": NOW.isoformat(),
        "total_count": len(localities),
        "healthy_count": healthy,
        "warning_count": warning_count,
        "critical_count": critical_count,
    }


# ── Locality detail ────────────────────────────────────────────────────────────

def get_locality_detail(locality_id: str) -> dict:
    cfg = get_locality_config(locality_id)
    data = get_locality_data(locality_id)
    confidence = compute_confidence(locality_id)
    source_data = get_source_status(locality_id)

    risk_now = data["risk_scores"][-1]
    delay_h = cfg["sync_delay_hours"]
    last_sync = (NOW - timedelta(hours=delay_h)).isoformat()

    return {
        "locality_id": locality_id,
        "locality_name": cfg["name"],
        "locality_no": cfg["locality_no"],
        "operator": cfg["operator"],
        "region": cfg["region"],
        "lat": cfg["lat"],
        "lon": cfg["lon"],
        "last_sync": last_sync,
        "sync_freshness": _sync_freshness(delay_h),
        "current_risk": risk_now,
        "confidence": confidence["overall"],
        "confidence_score": confidence["score"],
        "source_health": source_data["health_summary"],
        "available_periods": ["7d", "30d", "90d", "12m"],
    }


# ── Time series ────────────────────────────────────────────────────────────────

def get_timeseries(locality_id: str, period: str = "30d") -> dict:
    data = get_locality_data(locality_id)
    sliced_ts, start_idx = slice_by_period(data["timestamps"], period)
    n = len(sliced_ts)

    def _make_series(param: str, values: list, label: str, unit: str, color: str, threshold=None):
        points = []
        for i, ts in enumerate(sliced_ts):
            raw = values[start_idx + i]
            if raw is None:
                quality = "missing"
                val = None
            else:
                # Every 13th point marked as estimated for realism
                quality = "estimated" if (start_idx + i) % 13 == 0 else "observed"
                val = raw
            points.append({
                "timestamp": ts.isoformat(),
                "value": val,
                "quality": quality,
                "source": "BarentsWatch" if param != "treatment" else "derived",
            })
        return {"parameter": param, "label": label, "unit": unit, "color": color,
                "threshold": threshold, "chart_type": "line", "points": points}

    def _make_disease_series(values: list) -> dict:
        """Binary disease presence (0/1) — rendered as event-band, not line."""
        cfg = get_locality_config(locality_id)
        disease_name = cfg.get("disease_name") or None

        points = []
        for i, ts in enumerate(sliced_ts):
            val = int(values[start_idx + i])
            points.append({
                "timestamp": ts.isoformat(),
                "active": bool(val),
                "disease_name": disease_name if val else None,
                "source": "BarentsWatch",
            })

        # Build intervals with disease name attached
        intervals = []
        run_start = None
        for p in points:
            if p["active"] and run_start is None:
                run_start = p["timestamp"]
            elif not p["active"] and run_start is not None:
                intervals.append({
                    "start": run_start,
                    "end": p["timestamp"],
                    "disease_name": disease_name,
                })
                run_start = None
        if run_start is not None:
            intervals.append({
                "start": run_start,
                "end": points[-1]["timestamp"],
                "disease_name": disease_name,
            })

        has_active = any(p["active"] for p in points)
        return {
            "parameter": "disease",
            "label": "Sykdomsstatus",
            "disease_name": disease_name,
            "unit": "",
            "color": "#B91C1C",
            "chart_type": "event_band",
            "points": points,
            "intervals": intervals,
            "has_active": has_active,
        }

    return {
        "locality_id": locality_id,
        "locality_name": get_locality_config(locality_id)["name"],
        "period": period,
        "raw_data": [
            _make_series("lice", data["lice"], "Lakselus", "lus/fisk", "#7C3AED", threshold=1.0),
            _make_series("temperature", data["temperature"], "Temperatur", "°C", "#DC2626", threshold=14.0),
            _make_series("oxygen", data["oxygen"], "Oksygen", "mg/L", "#2563EB", threshold=7.0),
            _make_series("salinity", data["salinity"], "Salinitet", "ppt", "#0891B2"),
            _make_series("treatment", data["treatment"], "Behandlinger (30d)", "antall", "#6B7280"),
            _make_disease_series(data["disease"]),
        ],
        "available_periods": ["7d", "30d", "90d", "12m"],
    }


def get_risk_history(locality_id: str, period: str = "30d") -> dict:
    data = get_locality_data(locality_id)
    sliced_ts, start_idx = slice_by_period(data["timestamps"], period)

    history = []
    for i, ts in enumerate(sliced_ts):
        r = data["risk_scores"][start_idx + i]
        history.append({
            "timestamp": ts.isoformat(),
            "biological":    r["biological"],
            "structural":    r["structural"],
            "environmental": r["environmental"],
            "operational":   r["operational"],
            "total":         r["total"],
        })

    return {
        "locality_id": locality_id,
        "period": period,
        "risk_history": history,
    }


# ── C5AI+ risk overview (derived from live feed) ──────────────────────────────

# Kornstad Havbruk portfolio metadata — matches c5ai_mock.js
_C5AI_SITE_META: dict = {
    "KH_S01": {"site_name": "Kornstad", "biomass_tonnes": 3000, "biomass_value_nok": 195_000_000, "fjord_exposure": "semi_exposed"},
    "KH_S02": {"site_name": "Leite",    "biomass_tonnes": 2500, "biomass_value_nok": 162_500_000, "fjord_exposure": "semi_exposed"},
    "KH_S03": {"site_name": "Hogsnes",  "biomass_tonnes": 2800, "biomass_value_nok": 182_000_000, "fjord_exposure": "sheltered"},
}
_C5AI_OPERATOR_SITES = ["KH_S01", "KH_S02", "KH_S03"]
_C5AI_DOMAINS = ["biological", "structural", "environmental", "operational"]
_C5AI_ESTIMATED_ANNUAL_LOSS_NOK = 22_600_000


def get_c5ai_risk_overview() -> dict:
    """
    Derives C5AI+ risk overview (overall_risk_score, per-site scores, domain breakdown)
    from the current-day (last) risk score snapshot for each Kornstad Havbruk locality.

    These values update every time the live risk feed data is recalculated, so
    clicking "Oppdater feed" in Live Risk will propagate into Risk Intelligence scores.
    """
    total_biomass = sum(m["biomass_tonnes"] for m in _C5AI_SITE_META.values())
    site_rows = []
    domain_weighted = {d: 0.0 for d in _C5AI_DOMAINS}

    for lid in _C5AI_OPERATOR_SITES:
        data = get_locality_data(lid)
        risk = data["risk_scores"][-1]      # current day
        meta = _C5AI_SITE_META[lid]
        bshare = meta["biomass_tonnes"] / total_biomass

        # Dominant risks: top 2 domains by current score
        sorted_domains = sorted(_C5AI_DOMAINS, key=lambda d: risk[d], reverse=True)

        site_rows.append({
            "site_id":           lid,
            "site_name":         meta["site_name"],
            "biomass_tonnes":    meta["biomass_tonnes"],
            "biomass_value_nok": meta["biomass_value_nok"],
            "fjord_exposure":    meta["fjord_exposure"],
            "risk_score":        round(risk["total"], 1),
            "dominant_risks":    sorted_domains[:2],
        })

        for d in _C5AI_DOMAINS:
            domain_weighted[d] += risk[d] * bshare

    # Biomass-weighted overall score
    overall = round(
        sum(s["risk_score"] * s["biomass_tonnes"] / total_biomass for s in site_rows), 1
    )

    # Domain breakdown: each domain's share of the sum of weighted domain scores
    domain_total = sum(domain_weighted.values())
    domain_breakdown = {}
    for d in _C5AI_DOMAINS:
        frac = round(domain_weighted[d] / domain_total, 3) if domain_total > 0 else 0.25
        domain_breakdown[d] = {
            "fraction":         frac,
            "annual_loss_nok":  round(frac * _C5AI_ESTIMATED_ANNUAL_LOSS_NOK),
        }

    return {
        "overall_risk_score": overall,
        "sites":              site_rows,
        "domain_breakdown":   domain_breakdown,
        "generated_at":       NOW.isoformat(),
    }


# ── Cage impact (optional / indicative) ───────────────────────────────────────

def get_cage_impact(locality_id: str) -> dict:
    """
    Returns indicative cage-type exposure impact based on current domain risk.
    Not stochastic — uses domain multipliers as proxies for relative exposure.
    """
    from models.cage_technology import CAGE_DOMAIN_MULTIPLIERS
    data = get_locality_data(locality_id)
    current_risk = data["risk_scores"][-1]

    cage_impacts = []
    for cage_type, mults in CAGE_DOMAIN_MULTIPLIERS.items():
        # Weighted relative impact score
        impact_score = (
            mults["biological"]    * current_risk["biological"]    * 0.35 +
            mults["structural"]    * current_risk["structural"]    * 0.25 +
            mults["environmental"] * current_risk["environmental"] * 0.25 +
            mults["operational"]   * current_risk["operational"]   * 0.15
        )
        # Which domains are most affected?
        domain_scores = {
            d: mults[d] * current_risk[d]
            for d in ["biological", "structural", "environmental", "operational"]
        }
        top_domains = sorted(domain_scores, key=domain_scores.get, reverse=True)[:2]

        if impact_score > 30:
            relative_impact = "high"
        elif impact_score > 15:
            relative_impact = "medium"
        else:
            relative_impact = "low"

        cage_impacts.append({
            "cage_type": cage_type,
            "relative_impact": relative_impact,
            "impact_score": round(impact_score, 1),
            "affected_domains": top_domains,
            "explanation": _cage_explanation(cage_type, top_domains),
        })

    return {
        "locality_id": locality_id,
        "cage_impacts": cage_impacts,
        "note": "Indikativ eksponering basert på domenemultiplikatorer. Ikke stokastisk per-merd attribusjon.",
    }


def _cage_explanation(cage_type: str, top_domains: list) -> str:
    explanations = {
        "open_net":    "Åpen not er eksponert i alle domener — påvirkes direkte av lusenivå og miljøforhold",
        "semi_closed": "Semi-lukket har redusert biologisk eksponering, men økt driftsrisiko",
        "fully_closed": "Lukket merd har lav biologisk risiko, men høy strukturell og operasjonell sårbarhet",
        "submerged":   "Neddykket merd er godt skjermet mot overflatemiljø, men sårbar for strukturell belastning",
    }
    return explanations.get(cage_type, "Ukjent merdtype")

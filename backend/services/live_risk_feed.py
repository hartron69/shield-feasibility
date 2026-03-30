"""
backend/services/live_risk_feed.py

Assembles the feed overview and locality detail responses for the
Live Risk Intelligence module.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from backend.services.live_risk_mock import (
    get_all_locality_ids,
    get_locality_config,
    get_locality_data,
    slice_by_period,
    structural_fouling,
    structural_wave_load,
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
        last_sync = (datetime.now(timezone.utc) - timedelta(hours=delay_h)).isoformat()

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
        "last_updated": datetime.now(timezone.utc).isoformat(),
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
    last_sync = (datetime.now(timezone.utc) - timedelta(hours=delay_h)).isoformat()

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
        "generated_at":       datetime.now(timezone.utc).isoformat(),
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


# ── Site profile (Live Risk + BarentsWatch metadata) ─────────────────────────

# Operator-reported financial data — not available from BarentsWatch or Live Risk.
# Labelled separately so the frontend can show appropriate source badges.
_OPERATOR_FINANCIALS: dict = {
    "KH_S01": {"equipment_value_nok":  48_000_000, "infra_value_nok": 35_000_000, "annual_revenue_nok": 270_000_000, "operational_factor": 1.10},
    "KH_S02": {"equipment_value_nok":  42_000_000, "infra_value_nok": 30_000_000, "annual_revenue_nok": 225_000_000, "operational_factor": 1.00},
    "KH_S03": {"equipment_value_nok":  45_000_000, "infra_value_nok": 32_000_000, "annual_revenue_nok": 252_000_000, "operational_factor": 0.95},
}


def get_site_profile(locality_id: str) -> dict:
    """
    Returns the full site profile for a locality, combining:

    1. BarentsWatch live API (when BW_CLIENT_ID + BW_CLIENT_SECRET are set):
       company name, org number, GPS, MTB, species, licence ref — source: 'real'
    2. Locality config mock (fallback when BW credentials absent):
       same fields from _LOCALITY_CONFIG — source: 'derived'
    3. Operator-reported financials (equipment, infra, revenue) — source: 'operator'

    MTB (Maks Tillatt Biomasse) is the regulatory maximum from BW and differs
    from current_biomass_tonnes (the standing biomass in the water today).
    biomass_utilisation_pct = current / MTB × 100.
    """
    from backend.services.barentswatch_client import fetch_locality_registration

    cfg  = get_locality_config(locality_id)
    fin  = _OPERATOR_FINANCIALS.get(locality_id, {})

    # ── Try live BarentsWatch registration data ────────────────────────────────
    bw = fetch_locality_registration(cfg["locality_no"])
    bw_live = bw is not None

    # Prefer BW live values; fall back to mock config
    operator      = (bw or {}).get("company_name")    or cfg["operator"]
    lat           = (bw or {}).get("lat")              or cfg["lat"]
    lon           = (bw or {}).get("lon")              or cfg["lon"]
    site_name     = (bw or {}).get("site_name")        or cfg["name"]
    mtb           = (bw or {}).get("allowed_biomass")  or cfg.get("mtb_tonnes", 0)
    species       = (bw or {}).get("species")          or cfg.get("species", "Atlantisk laks (Salmo salar)")
    licence_ref   = (bw or {}).get("licence_ref")      or cfg.get("license_number")
    org_number    = (bw or {}).get("org_number")
    municipality  = (bw or {}).get("municipality")     or cfg["region"]
    bw_status     = (bw or {}).get("status")

    # ── Derived fields ─────────────────────────────────────────────────────────
    exp_cls   = _exposure_class(cfg["exposure"])
    current_b = cfg.get("biomass_tonnes", 0)
    util_pct  = round(current_b / mtb * 100, 1) if mtb else None

    start_year = cfg.get("start_year")
    years_op   = (NOW.year - start_year) if start_year else None
    biomass_value_nok = current_b * 65_000

    reg_source = "real" if bw_live else "derived"

    return {
        "locality_id":   locality_id,
        "site_name":     site_name,
        "locality_no":   cfg["locality_no"],
        "operator":      operator,
        "org_number":    org_number,
        "region":        municipality,
        "lat":           lat,
        "lon":           lon,
        "species":       species,
        "exposure_factor":  cfg["exposure"],
        "exposure_class":   exp_cls,
        # BarentsWatch Akvakulturregisteret fields
        "mtb_tonnes":              mtb,
        "current_biomass_tonnes":  current_b,
        "biomass_utilisation_pct": util_pct,
        "license_number":          licence_ref,
        "start_year":              start_year,
        "years_in_operation":      years_op,
        "nis_certified":           cfg.get("nis_certified", False),
        "bw_status":               bw_status,
        "biomass_value_nok":       biomass_value_nok,
        # Operator-reported financials
        "equipment_value_nok":  fin.get("equipment_value_nok"),
        "infra_value_nok":      fin.get("infra_value_nok"),
        "annual_revenue_nok":   fin.get("annual_revenue_nok"),
        "operational_factor":   fin.get("operational_factor"),
        # Source labels per field group — drives badge rendering in frontend
        "sources": {
            "registration": reg_source,   # 'real' = live BW, 'derived' = mock config
            "position":     reg_source,
            "mtb":          reg_source,
            "exposure":     "derived",    # Live Risk model config
            "financials":   "operator",   # operator-reported
        },
        "bw_live": bw_live,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Inputs snapshot (derived from Live Risk model) ────────────────────────────

def _exposure_class(exposure: float) -> str:
    if exposure >= 1.1:
        return "open"
    elif exposure >= 0.9:
        return "semi"
    return "sheltered"


def _reading(parameter: str, value, baseline, unit: str, adverse: bool, description: str = None) -> dict:
    return {
        "parameter": parameter,
        "value":     value,
        "baseline":  baseline,
        "unit":      unit,
        "adverse":   adverse,
        "description": description,
    }


def get_inputs_snapshot(locality_id: str) -> dict:
    """
    Derive per-domain input snapshots from the Live Risk model for a locality.

    All four domains (structural, environmental, operational, biological) are
    computed from the same underlying time-series and risk functions used by the
    Live Risk feed — no separate mock data needed.
    """
    data = get_locality_data(locality_id)
    cfg  = get_locality_config(locality_id)

    d        = DAYS - 1
    exposure = cfg["exposure"]
    exp_cls  = _exposure_class(exposure)
    recorded = datetime.now(timezone.utc).isoformat()

    # ── Structural drivers ─────────────────────────────────────────────────────
    fouling   = structural_fouling(d)
    wave      = structural_wave_load(d, exposure)
    # Normalise wave to [0, 1]: min = exposure*0.4, max = exposure*1.6, range = exposure*1.2
    wave_norm = max(0.0, min(1.0, (wave - exposure * 0.4) / (exposure * 1.2)))
    tr_now    = data["treatment"][d]
    lining    = 1.0 if tr_now > 2 else 0.0
    struct_score = data["risk_scores"][d]["structural"]

    structural = {
        "source": "derived",
        "readings": [
            _reading("Biofouling-indeks",
                     round(fouling, 2), 0.30, "indeks",
                     fouling > 0.65,
                     "Sesongbasert biofilmakkumulering (0=vinterbunnen, 1=sommermaks). "
                     "Høy fouling øker notslitasje og reduserer gjennomstrømning."),
            _reading("Bølgebelastningsindeks",
                     round(wave_norm, 2), 0.50, "indeks",
                     wave_norm > 0.70,
                     "Normalisert bølge-/stormbelastning for nåværende sesong og "
                     f"eksponeringsklasse ({exp_cls}). 1.0 = vintermaksimum."),
            _reading("Driftsbelastning not",
                     round(lining, 0), 0.0, "0/1",
                     lining > 0,
                     "Notbelastning fra intensiv behandling (>2 behandlinger siste 30d). "
                     "Håndtering under behandling øker strukturell slitasje."),
            _reading("Strukturell risikoskår",
                     round(struct_score, 1), 15.0, "poeng",
                     struct_score > 25.0,
                     "Aggregert strukturell risikoskår fra Live Risk-modellen: "
                     "eksponering + biofouling + bølgebelastning + driftsbelastning."),
            _reading("Eksponeringsklasse",
                     exp_cls, "semi", "",
                     exp_cls == "open",
                     f"Eksponeringskoeffisient: {exposure:.2f}. "
                     "Åpen kyst > 1.1, semi-eksponert 0.9–1.1, skjermet < 0.9."),
        ],
    }

    # ── Environmental drivers ──────────────────────────────────────────────────
    temp_now = data["temperature"][d] or cfg["temp_base"]
    oxy_now  = data["oxygen"][d]  or cfg["oxygen_base"]
    # Sig. wave height: scale wave_norm linearly; range ~0.3–4.0 m depending on exposure
    sig_wave = round(max(0.1, wave_norm * 3.5 * min(exposure, 1.3)), 1)
    # Current speed (m/s): proportional to wave load
    current  = round(max(0.05, wave_norm * (0.25 + exposure * 0.55)), 2)
    # O2 saturation: 100% ≈ 11.0 mg/L at ~10 °C Norwegian coastal water
    oxy_sat  = round(min(130.0, oxy_now / 11.0 * 100.0), 1)
    # Ice risk: static by exposure class (open coast rarely freezes, sheltered fjord may)
    ice_risk = {"open": 0.01, "semi": 0.03, "sheltered": 0.09}.get(exp_cls, 0.03)
    env_score = data["risk_scores"][d]["environmental"]

    environmental = {
        "source": "derived",
        "readings": [
            _reading("Løst O₂",
                     round(oxy_now, 1), 8.5, "mg/L",
                     oxy_now < 7.0,
                     "Under trygg minimumsterskel på 7 mg/L — stressrisiko aktiv." if oxy_now < 7.0 else None),
            _reading("O₂-metning",
                     oxy_sat, 95.0, "%",
                     oxy_sat < 80.0,
                     "Under 80 % metningsterskel." if oxy_sat < 80.0 else None),
            _reading("Overflatetemperatur",
                     round(temp_now, 1), 12.0, "°C",
                     temp_now > 16.0 or temp_now < 4.0,
                     "Over sikker øvre grense (16 °C) — HAB og patogenrisiko forhøyet." if temp_now > 16.0
                     else ("Under sikker nedre grense (4 °C)." if temp_now < 4.0 else None)),
            _reading("Signifikant bølgehøyde (est.)",
                     sig_wave, 1.5, "m",
                     sig_wave > 2.0,
                     "Estimert fra sesongbasert bølgebelastningsmodell og eksponeringsklasse."),
            _reading("Strømhastighet (est.)",
                     current, 0.40, "m/s",
                     current > 0.60,
                     "Overskrider designgrense 0.60 m/s." if current > 0.60 else None),
            _reading("Isrisikoskår",
                     ice_risk, 0.05, "skår",
                     ice_risk > 0.05),
            _reading("Eksponeringsklasse",
                     exp_cls, "semi", "",
                     exp_cls == "open"),
            _reading("Miljørisikoskår",
                     round(env_score, 1), 15.0, "poeng",
                     env_score > 25.0,
                     "Aggregert miljørisiko: temperaturavvik + oksygenstress."),
        ],
    }

    # ── Operational drivers ────────────────────────────────────────────────────
    ops_score   = data["risk_scores"][d]["operational"]
    # Maintenance backlog: treatment intensity + ops score contribution
    backlog = round(min(0.90, max(0.0, tr_now / 12.0 + ops_score / 180.0)), 2)
    # Equipment readiness: inverse of operational risk
    equip   = round(max(0.25, min(1.0, 1.0 - ops_score / 100.0 * 0.55)), 2)
    # Staffing and training: scaled from ops score (lower ops score = better staffing)
    staffing = round(max(0.30, min(1.0, 1.0 - ops_score / 100.0 * 0.50)), 2)
    training = round(max(40.0, min(100.0, 100.0 - ops_score * 0.40)), 1)
    # Incident rate: treatment events as proxy
    incident = round(min(4.0, tr_now / 6.0 + ops_score / 70.0), 2)

    operational = {
        "source": "derived",
        "readings": [
            _reading("Behandlingsbyrde (30d)",
                     float(tr_now), 2.0, "behandlinger",
                     tr_now > 4,
                     "Rullerende 30-dagers behandlingsantall — direkte fra Live Risk-modellen. "
                     "Proxy for frekvens av høyrisikooperasjoner."),
            _reading("Vedlikeholdsetterslep",
                     backlog, 0.20, "skår",
                     backlog > 0.35,
                     "Avledet av behandlingsintensitet og operasjonell risikoskår. "
                     "Høy behandlingsfrekvens øker etterslep på planlagt vedlikehold."),
            _reading("Utstyrsberedskap (est.)",
                     equip, 0.80, "skår",
                     equip < 0.70,
                     "Estimert fra operasjonell risikoskår — høy risikoskår reduserer estimert beredskap."),
            _reading("Bemanningsskår (est.)",
                     staffing, 0.75, "skår",
                     staffing < 0.65,
                     "Estimert fra operasjonell risikoskår. Ikke rapportert fra operatør."),
            _reading("Opplæringsoverholdelse (est.)",
                     training, 90.0, "%",
                     training < 80.0,
                     "Estimert fra operasjonell risikoskår. Ikke rapportert fra operatør."),
            _reading("Hendelsesrate (est.)",
                     incident, 0.5, "/mnd",
                     incident > 1.0,
                     "Estimert fra behandlingsfrekvens og operasjonell risikoskår."),
            _reading("Operasjonell risikoskår",
                     round(ops_score, 1), 10.0, "poeng",
                     ops_score > 20.0,
                     "Aggregert operasjonell risiko fra Live Risk-modellen: behandlingsbyrde + støy."),
        ],
    }

    # ── Biological (disease + lice snapshot) ──────────────────────────────────
    lice_now      = data["lice"][d]
    disease_now   = bool(data["disease"][d])
    disease_name  = cfg.get("disease_name") or None
    bio_score     = data["risk_scores"][d]["biological"]

    biological = {
        "source": "derived",
        "disease_active": disease_now,
        "disease_name":   disease_name,
        "lice_now":       round(lice_now, 3) if lice_now is not None else None,
        "treatment_30d":  int(tr_now),
        "bio_score":      round(bio_score, 1),
        "readings": [
            _reading("Lakselus (siste obs.)",
                     round(lice_now, 2) if lice_now is not None else None,
                     0.5, "lus/fisk",
                     (lice_now or 0) > 1.0,
                     "Over behandlingsterskel på 1.0 lus/fisk." if (lice_now or 0) > 1.0 else None),
            _reading("Sykdomsstatus",
                     1 if disease_now else 0, 0, "0/1",
                     disease_now,
                     f"Aktiv: {disease_name}" if disease_now and disease_name else
                     ("Aktiv sykdomsstatus" if disease_now else None)),
            _reading("Behandlinger (30d)",
                     float(tr_now), 2.0, "behandlinger",
                     tr_now > 4),
            _reading("Biologisk risikoskår",
                     round(bio_score, 1), 20.0, "poeng",
                     bio_score > 35.0,
                     "Aggregert biologisk risiko: lakselus + sykdomsstatus + eksponering."),
        ],
    }

    return {
        "locality_id":   locality_id,
        "locality_name": cfg["name"],
        "recorded_at":   recorded,
        "structural":    structural,
        "environmental": environmental,
        "operational":   operational,
        "biological":    biological,
    }


# ── Pattern signals (derived from Live Risk + PatternDetector) ────────────────

# One representative risk_type per domain for multi-domain signal detection.
# Biological types each have unique rules; structural/env/ops share a rule set.
_SIGNAL_RISK_TYPES = [
    ("biological",   "hab"),
    ("biological",   "lice"),
    ("biological",   "jellyfish"),
    ("biological",   "pathogen"),
    ("structural",   "mooring_failure"),
    ("environmental","oxygen_stress"),
    ("operational",  "human_error"),
]


def get_pattern_signals(locality_id: str) -> dict:
    """
    Run PatternDetector for 7 representative risk types using live env_data
    derived from the Live Risk model. Returns signal records for the
    Alert Signals panel — no hardcoded mock values.
    """
    from c5ai_plus.alerts.pattern_detector import PatternDetector

    data    = get_locality_data(locality_id)
    cfg     = get_locality_config(locality_id)
    d       = DAYS - 1
    exposure = cfg["exposure"]
    exp_cls  = _exposure_class(exposure)

    # ── Raw current values ─────────────────────────────────────────────────
    temp_now  = data["temperature"][d] or cfg["temp_base"]
    oxy_now   = data["oxygen"][d]      or cfg["oxygen_base"]
    lice_now  = data["lice"][d]        or 0.0
    tr_now    = int(data["treatment"][d])

    wave      = structural_wave_load(d, exposure)
    wave_norm = max(0.0, min(1.0, (wave - exposure * 0.4) / (exposure * 1.2)))
    current_speed = max(0.05, wave_norm * (0.25 + exposure * 0.55))
    ice_risk  = {"open": 0.01, "semi": 0.03, "sheltered": 0.09}.get(exp_cls, 0.03)

    risk      = data["risk_scores"][d]
    ops_score = risk["operational"]
    backlog   = min(0.90, max(0.0, tr_now / 12.0 + ops_score / 180.0))
    equip     = max(0.25, min(1.0, 1.0 - ops_score / 100.0 * 0.55))
    staffing  = max(0.30, min(1.0, 1.0 - ops_score / 100.0 * 0.50))
    training  = max(40.0, min(100.0, 100.0 - ops_score * 0.40))

    # ── env_data dict — keys match PatternDetector._evaluate_rule() ───────
    env_data = {
        "surface_temp_c":           temp_now,
        "water_temp_c":             temp_now,
        "dissolved_oxygen_mg_l":    oxy_now,
        "lice_count_per_fish":      lice_now,
        "treatments_last_12m":      float(tr_now * 4),   # 30d proxy → annual
        "handling_events_last_30d": float(tr_now),
        "open_coast_flag":          1.0 if exp_cls == "open" else (0.5 if exp_cls == "semi" else 0.1),
        "month":                    datetime.now(timezone.utc).month,
        "current_speed_ms":         round(current_speed, 3),
        "ice_risk_score":           ice_risk,
        "combined_exposure_score":  round(wave_norm * (1.0 if exp_cls == "open" else 0.5), 3),
        "staffing_score":           staffing,
        "training_compliance_pct":  training,
        "equipment_readiness_score": equip,
        "maintenance_backlog_score": backlog,
    }

    # Domain probability: current domain risk score scaled to [0, 1]
    domain_prob = {
        "biological":   risk["biological"]    / 100.0,
        "structural":   risk["structural"]    / 100.0,
        "environmental":risk["environmental"] / 100.0,
        "operational":  risk["operational"]   / 100.0,
    }

    detector  = PatternDetector()
    site_name = cfg["name"]
    all_signals: list = []

    for domain, risk_type in _SIGNAL_RISK_TYPES:
        prob = domain_prob[domain]
        _, signals = detector.detect(locality_id, risk_type, prob, env_data)
        for sig in signals:
            all_signals.append({
                "site_id":        locality_id,
                "site_name":      site_name,
                "domain":         domain,
                "risk_type":      risk_type,
                "signal_name":    sig.signal_name,
                "current_value":  round(float(sig.current_value), 4),
                "baseline_value": round(float(sig.baseline_value), 4),
                "delta":          round(float(sig.current_value - sig.baseline_value), 4),
                "z_score":        round(float(sig.z_score), 3),
                "threshold":      float(sig.threshold),
                "triggered":      sig.triggered,
                "direction":      sig.direction,
            })

    triggered_count = sum(1 for s in all_signals if s["triggered"])

    return {
        "locality_id":     locality_id,
        "locality_name":   site_name,
        "signals":         all_signals,
        "total_signals":   len(all_signals),
        "triggered_count": triggered_count,
        "generated_at":    datetime.now(timezone.utc).isoformat(),
    }


# ── Data quality (derived from Live Risk model) ───────────────────────────────

# Per-risk-type quality spec:
#   (source, lr_param | None, quality_cap, missing_fields)
#
# source        — 'derived' | 'simulated' | 'estimated'
# lr_param      — key in get_locality_data() to compute actual non-null fraction
#                 (None = no Live Risk equivalent, use quality_cap directly)
# quality_cap   — maximum completeness score; reflects that model-derived data
#                 is not equivalent to direct sensor measurements
# missing_fields — field names not available in the current feed
_DQ_SPECS: dict = {
    # ── Biological ──
    "lice":                ("derived",   "lice",        1.00, []),
    "hab":                 ("simulated", "temperature", 0.72, ["chlorophyll_history", "nitrate_series", "algae_species"]),
    "jellyfish":           ("simulated", None,          0.40, ["current_data", "bloom_index", "species_id"]),
    "pathogen":            ("simulated", "disease",     0.65, ["pcr_results", "mortality_records"]),
    # ── Structural (all derived from treatment + fouling + wave model) ──
    "mooring_failure":     ("derived",   "treatment",   0.75, ["anchor_tensile_test", "corrosion_survey"]),
    "net_integrity":       ("derived",   "treatment",   0.78, ["net_mesh_survey"]),
    "cage_structural":     ("derived",   "treatment",   0.72, ["deformation_log", "load_cell_data"]),
    "deformation":         ("derived",   "treatment",   0.73, ["load_cell_data", "deformation_log"]),
    "anchor_deterioration":("derived",   "treatment",   0.70, ["tensile_test"]),
    # ── Environmental ──
    "oxygen_stress":       ("derived",   "oxygen",      1.00, []),
    "temperature_extreme": ("derived",   "temperature", 1.00, []),
    "current_storm":       ("derived",   None,          0.65, ["wave_buoy_data", "current_meter"]),
    "ice":                 ("estimated", None,          0.50, ["sea_level_gauge", "ice_forecast"]),
    "exposure_anomaly":    ("estimated", None,          0.45, ["current_meter", "exposure_model"]),
    # ── Operational ──
    "maintenance_backlog": ("derived",   "treatment",   0.88, []),
    "human_error":         ("estimated", None,          0.45, ["incident_reports", "training_records"]),
    "procedure_failure":   ("estimated", None,          0.50, ["procedure_audit_log"]),
    "equipment_failure":   ("estimated", None,          0.55, ["maintenance_log", "failure_history"]),
    "incident":            ("estimated", None,          0.52, ["near_miss_reports"]),
}

_WINDOW = 90  # days


def get_data_quality(locality_id: str) -> dict:
    """
    Compute actual data quality metrics for all 19 risk types using Live Risk data.

    Completeness is derived from the actual non-null fraction in the Live Risk
    feed for parameters that have a direct equivalent (lice, temperature, oxygen,
    treatment, disease). For model-derived parameters (structural, operational
    estimates) a quality cap is applied to reflect the difference between a
    computed estimate and a real sensor measurement. Parameters genuinely absent
    from the feed (jellyfish bloom, PCR results, etc.) receive their cap value
    directly with honest missing_fields lists.
    """
    from backend.services.confidence_scoring import compute_confidence

    data = get_locality_data(locality_id)
    cfg  = get_locality_config(locality_id)

    # Actual non-null fractions for each Live Risk param in the last _WINDOW days
    def _frac(param_key: str):
        window = data[param_key][-_WINDOW:]
        n_non_null = sum(1 for v in window if v is not None)
        return n_non_null / len(window), n_non_null

    lr_fracs = {
        "lice":        _frac("lice"),
        "temperature": _frac("temperature"),
        "oxygen":      _frac("oxygen"),
        "treatment":   _frac("treatment"),
        "disease":     _frac("disease"),
    }

    def _flag(c: float) -> str:
        if c >= 0.80: return "SUFFICIENT"
        if c >= 0.60: return "LIMITED"
        if c >  0.0:  return "POOR"
        return "MISSING"

    def _conf(c: float, source: str) -> str:
        if source == "estimated":
            return "medium" if c >= 0.60 else "low"
        return "high" if c >= 0.80 else ("medium" if c >= 0.60 else "low")

    risk_types: dict = {}
    for rt, (source, lr_param, cap, missing_fields) in _DQ_SPECS.items():
        if lr_param is not None:
            actual_frac, n_obs = lr_fracs[lr_param]
            completeness = min(actual_frac, cap)
        else:
            completeness = cap
            n_obs = round(cap * _WINDOW)

        risk_types[rt] = {
            "source":         source,
            "completeness":   round(completeness, 3),
            "confidence":     _conf(completeness, source),
            "flag":           _flag(completeness),
            "n_obs":          n_obs,
            "missing_fields": missing_fields,
        }

    # Overall completeness: unweighted mean across all risk types
    overall_completeness = round(
        sum(v["completeness"] for v in risk_types.values()) / len(risk_types), 3
    )

    # Overall confidence from existing confidence_scoring service
    conf = compute_confidence(locality_id)
    overall_confidence = conf["overall"]

    return {
        "locality_id":          locality_id,
        "locality_name":        cfg["name"],
        "overall_completeness": overall_completeness,
        "overall_confidence":   overall_confidence,
        "risk_types":           risk_types,
        "generated_at":         datetime.now(timezone.utc).isoformat(),
    }

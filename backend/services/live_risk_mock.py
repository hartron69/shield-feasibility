"""
backend/services/live_risk_mock.py

Deterministic synthetic data generator for the Live Risk Intelligence module.

Generates 365 days (one full year) of realistic daily measurements for each monitored locality.
All data is seeded for consistency across API calls and restarts.

Localities:
  KH_S01 (Kornstad)  — moderate lice, one disease event ~30d ago, semi-exposed
  KH_S02 (Leite)     — higher biological variation, one delayed source
  KH_S03 (Hogsnes)   — cleanest data, sheltered, lowest baseline risk (Kornstad Havbruk)
  LM_S01 (Hogsnes)   — Lerøy Midt Sjø AS, neighbouring cage site, higher exposure
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── Constants ──────────────────────────────────────────────────────────────────

NOW = datetime(2026, 3, 27, 10, 0, 0, tzinfo=timezone.utc)
DAYS = 365  # one full year of history (27 March 2025 – 27 March 2026)

# Locality seeds and baseline profiles.
# Event days are expressed as absolute day index from start (day 0 = ~27 March 2025).
# "N days ago" = DAYS - 1 - spike_day.
_LOCALITY_CONFIG: Dict[str, dict] = {
    "KH_S01": {
        "seed": 101,
        "name": "Kornstad",
        "locality_no": 12855,
        "operator": "Kornstad Havbruk AS",
        "region": "Møre og Romsdal",
        "lat": 62.960383, "lon": 7.45015,
        "exposure": 1.15,
        # ── Site profile (BarentsWatch Akvakulturregisteret) ───────────────
        "mtb_tonnes":      3900,   # Maks Tillatt Biomasse (regulatory maximum)
        "biomass_tonnes":  3000,   # current standing biomass
        "species":         "Atlantisk laks (Salmo salar)",
        "license_number":  "AK-MR-12855",
        "start_year":      2019,
        "nis_certified":   True,
        # ── Time-series simulation ─────────────────────────────────────────
        "lice_base": 0.42,
        "lice_spike_day": 333,  # 364-333 = 31 days ago
        "lice_spike_mag": 0.8,
        "disease_day": 335,     # disease onset 29 days ago; resolves at day 347 (~17d ago)
        "disease_name": "Pancreas disease (PD)",
        "temp_base": 6.8,
        "temp_amp": 2.1,
        "oxygen_base": 8.9,
        "sync_delay_hours": 1.5,
        "source_degraded": None,
    },
    "KH_S02": {
        "seed": 202,
        "name": "Leite",
        "locality_no": 12870,
        "operator": "Kornstad Havbruk AS",
        "region": "Møre og Romsdal",
        "lat": 63.03515, "lon": 7.676817,
        "exposure": 1.10,
        # ── Site profile ───────────────────────────────────────────────────
        "mtb_tonnes":      3120,
        "biomass_tonnes":  2500,
        "species":         "Atlantisk laks (Salmo salar)",
        "license_number":  "AK-MR-12870",
        "start_year":      2015,
        "nis_certified":   True,
        # ── Time-series simulation ─────────────────────────────────────────
        "lice_base": 0.55,
        "lice_spike_day": 320,  # 364-320 = 44 days ago
        "lice_spike_mag": 1.1,
        "disease_day": None,
        "disease_name": None,
        "temp_base": 6.5,
        "temp_amp": 1.8,
        "oxygen_base": 9.1,
        "sync_delay_hours": 18.0,   # one source delayed
        "source_degraded": "bw_environmental",
    },
    "KH_S03": {
        "seed": 303,
        "name": "Hogsnes",
        "locality_no": 12871,
        "operator": "Kornstad Havbruk AS",
        "region": "Møre og Romsdal",
        "lat": 63.093033, "lon": 7.675883,
        "exposure": 0.85,
        # ── Site profile ───────────────────────────────────────────────────
        "mtb_tonnes":      3600,
        "biomass_tonnes":  2800,
        "species":         "Atlantisk laks (Salmo salar)",
        "license_number":  "AK-MR-12871",
        "start_year":      2014,
        "nis_certified":   True,
        # ── Time-series simulation ─────────────────────────────────────────
        "lice_base": 0.18,
        "lice_spike_day": None,
        "lice_spike_mag": 0.0,
        "disease_day": None,
        "disease_name": None,
        "temp_base": 6.2,
        "temp_amp": 1.5,
        "oxygen_base": 9.4,
        "sync_delay_hours": 0.8,
        "source_degraded": None,
    },
    "LM_S01": {
        "seed": 404,
        "name": "Hogsneset N",
        "locality_no": 30377,
        "operator": "Lerøy Midt Sjø AS",
        "region": "Møre og Romsdal",
        "lat": 63.097, "lon": 7.682,
        "exposure": 1.05,
        "lice_base": 0.31,
        "lice_spike_day": 325,  # 364-325 = 39 days ago
        "lice_spike_mag": 0.7,
        "disease_day": None,
        "disease_name": None,
        "temp_base": 6.3,
        "temp_amp": 1.6,
        "oxygen_base": 9.1,
        "sync_delay_hours": 3.5,
        "source_degraded": None,
    },
}

_SOURCE_DEFINITIONS = [
    {"source_id": "bw_lice",         "source_name": "BW Lakselus",        "source_type": "BarentsWatch"},
    {"source_id": "bw_disease",      "source_name": "BW Sykdomsstatus",   "source_type": "BarentsWatch"},
    {"source_id": "bw_environmental","source_name": "BW Miljødata",       "source_type": "BarentsWatch"},
    {"source_id": "norkyst",         "source_name": "NorKyst / Met",      "source_type": "NorKyst"},
    {"source_id": "c5ai_risk",       "source_name": "C5AI+ Risikomodell", "source_type": "C5AI+"},
]


# ── Structural risk helpers (shared with risk_change_explainer) ────────────────

def structural_fouling(d: int) -> float:
    """Seasonal biofouling index [0–1].
    Day 0 = 27 March. Peaks in Norwegian summer (~day 120, late July) when
    algae and blue mussel growth on nets is highest. Near zero in winter.
    """
    return 0.5 + 0.5 * math.sin(2 * math.pi * (d - 29) / 365)


def structural_wave_load(d: int, exposure: float) -> float:
    """Seasonal wave/storm load [~0.4–1.8 × exposure].
    Peaks in Norwegian winter (~day 280, late December) when North Atlantic
    low-pressure systems dominate. Lowest in summer.
    """
    return exposure * (1.0 + 0.6 * math.cos(2 * math.pi * (d - 280) / 365))


# ── Time series generation ─────────────────────────────────────────────────────

def _days_back(d: int) -> datetime:
    return NOW - timedelta(days=DAYS - 1 - d)


def _gen_lice(cfg: dict, rng: np.random.Generator) -> List[Optional[float]]:
    base = cfg["lice_base"]
    spike_day = cfg["lice_spike_day"]
    spike_mag = cfg["lice_spike_mag"]
    values = []
    for d in range(DAYS):
        noise = rng.normal(0, 0.06)
        trend = base + 0.002 * d
        if spike_day and abs(d - spike_day) < 8:
            dist = abs(d - spike_day)
            spike = spike_mag * math.exp(-dist * 0.5)
            val = trend + spike + noise
        else:
            val = trend + noise
        # 5% missing
        if rng.random() < 0.05:
            values.append(None)
        else:
            values.append(max(0.0, round(val, 3)))
    return values


def _gen_temperature(cfg: dict, rng: np.random.Generator) -> List[Optional[float]]:
    base = cfg["temp_base"]
    amp = cfg["temp_amp"]
    values = []
    for d in range(DAYS):
        seasonal = amp * math.sin(2 * math.pi * (d - 30) / 365)
        noise = rng.normal(0, 0.3)
        val = base + seasonal + noise
        if rng.random() < 0.03:
            values.append(None)
        else:
            values.append(round(val, 2))
    return values


def _gen_oxygen(cfg: dict, rng: np.random.Generator) -> List[Optional[float]]:
    base = cfg["oxygen_base"]
    values = []
    for d in range(DAYS):
        noise = rng.normal(0, 0.2)
        val = base + noise
        if rng.random() < 0.04:
            values.append(None)
        else:
            values.append(round(max(5.0, val), 2))
    return values


def _gen_salinity(cfg: dict, rng: np.random.Generator) -> List[Optional[float]]:
    values = []
    for d in range(DAYS):
        val = 33.5 + rng.normal(0, 0.4)
        if rng.random() < 0.03:
            values.append(None)
        else:
            values.append(round(val, 2))
    return values


def _gen_disease(cfg: dict, rng: np.random.Generator) -> List[int]:
    disease_day = cfg["disease_day"]
    values = []
    for d in range(DAYS):
        if disease_day and disease_day <= d <= disease_day + 12:
            values.append(1)
        else:
            values.append(0)
    return values


def _gen_treatment(lice: List[Optional[float]], disease: List[int]) -> List[int]:
    """Rolling 30-day treatment count derived from lice + disease signals."""
    events = []
    for d in range(DAYS):
        lv = lice[d] or 0.0
        if lv > 1.0 or disease[d] == 1:
            events.append(1)
        elif lv > 0.5 and d % 7 == 0:
            events.append(1)
        else:
            events.append(0)
    # rolling 30-day sum
    result = []
    for d in range(DAYS):
        start = max(0, d - 29)
        result.append(sum(events[start:d + 1]))
    return result


# ── Risk score derivation ──────────────────────────────────────────────────────

def _compute_risk(
    lice: List[Optional[float]],
    disease: List[int],
    temperature: List[Optional[float]],
    oxygen: List[Optional[float]],
    treatment: List[int],
    cfg: dict,
) -> List[Dict[str, float]]:
    exposure = cfg["exposure"]
    scores = []
    for d in range(DAYS):
        lv = lice[d] or 0.0
        dv = disease[d]
        tv = temperature[d] or cfg["temp_base"]
        ov = oxygen[d] or cfg["oxygen_base"]
        tr = treatment[d]

        # Biological: lice + disease
        bio = min(100, (lv / 2.0) * 60 * exposure + dv * 25 + rng_noise(d, "bio"))
        bio = max(0, bio)

        # Structural: biofouling + wave/storm load + net operations
        fouling   = structural_fouling(d)          # seasonal biofouling (0–1)
        wave      = structural_wave_load(d, exposure)  # seasonal wave load
        lining    = 1.0 if tr > 2 else 0.0        # net handling during intensive treatment
        struct = min(100, max(0,
            8 * exposure          # baseline (location/exposure)
            + fouling * 12        # biofouling contribution
            + wave * 6            # wave/current/storm load
            + lining * 8          # net operations load
            + rng_noise(d, "str")
        ))

        # Environmental: temperature anomaly + oxygen stress
        temp_anom = max(0, tv - 10.0)
        oxy_stress = max(0, 9.0 - ov)
        env = min(100, 10 + temp_anom * 8 + oxy_stress * 12 + rng_noise(d, "env"))
        env = max(0, env)

        # Operational: treatment burden + complexity
        ops = min(100, 8 + tr * 3 + rng_noise(d, "ops"))
        ops = max(0, ops)

        total = round(0.35 * bio + 0.25 * struct + 0.25 * env + 0.15 * ops, 1)
        scores.append({
            "biological": round(bio, 1),
            "structural": round(struct, 1),
            "environmental": round(env, 1),
            "operational": round(ops, 1),
            "total": total,
        })
    return scores


def rng_noise(day: int, domain: str, scale: float = 2.0) -> float:
    """Deterministic pseudo-noise — used inside _compute_risk."""
    h = hash(f"{day}{domain}") & 0xFFFF
    return (h / 0xFFFF - 0.5) * scale * 2


# ── Public API ─────────────────────────────────────────────────────────────────

def _build_locality_data(locality_id: str) -> dict:
    cfg = _LOCALITY_CONFIG[locality_id]
    rng = np.random.default_rng(cfg["seed"])

    lice = _gen_lice(cfg, rng)
    temperature = _gen_temperature(cfg, rng)
    oxygen = _gen_oxygen(cfg, rng)
    salinity = _gen_salinity(cfg, rng)
    disease = _gen_disease(cfg, rng)
    treatment = _gen_treatment(lice, disease)
    risk_scores = _compute_risk(lice, disease, temperature, oxygen, treatment, cfg)

    timestamps = [_days_back(d) for d in range(DAYS)]

    return {
        "config": cfg,
        "timestamps": timestamps,
        "lice": lice,
        "temperature": temperature,
        "oxygen": oxygen,
        "salinity": salinity,
        "disease": disease,
        "treatment": treatment,
        "risk_scores": risk_scores,
    }


# Module-level cache (built once per process start)
_CACHE: Dict[str, dict] = {}


def get_locality_data(locality_id: str) -> dict:
    if locality_id not in _CACHE:
        _CACHE[locality_id] = _build_locality_data(locality_id)
    return _CACHE[locality_id]


def get_all_locality_ids() -> List[str]:
    return list(_LOCALITY_CONFIG.keys())


def get_locality_config(locality_id: str) -> dict:
    return _LOCALITY_CONFIG[locality_id]


def get_source_definitions() -> List[dict]:
    return _SOURCE_DEFINITIONS


def period_to_days(period: str) -> int:
    return {"7d": 7, "30d": 30, "90d": 90, "12m": 365}.get(period, 30)


def slice_by_period(data: list, period: str) -> Tuple[list, int]:
    """Return the last N days of a 90-day list, plus the start index."""
    n = min(period_to_days(period), DAYS)
    start = max(0, DAYS - n)
    return data[start:], start

"""
c5ai_plus/Barentswatch/bw_to_c5ai_adapter.py

Converts BarentsWatch fetcher output files into a C5AIOperatorInput that
can be passed directly to ForecastPipeline.

Reads per-site:
  luse_historikk_{no}.csv      → List[LiceObservation] + List[EnvironmentalObservation]
  sykdom_historikk_{no}.json   → List[PathogenObservation]
  risk_forecast_{no}.json      → data quality flag, scale factor metadata

Usage
-----
    from c5ai_plus.Barentswatch.bw_to_c5ai_adapter import (
        bw_data_available,
        bw_data_to_operator_input,
        bw_quality_summary,
    )

    if bw_data_available():
        op_input = bw_data_to_operator_input()
        # op_input is a fully-formed C5AIOperatorInput
"""

from __future__ import annotations

import csv
import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from c5ai_plus.data_models.biological_input import (
    C5AIOperatorInput,
    EnvironmentalObservation,
    LiceObservation,
    PathogenObservation,
    SiteMetadata,
)
from c5ai_plus.Barentswatch.bw_config import (
    BW_DATA_DIR,
    DEFAULT_OPERATOR_CFG,
)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _week_to_month(year: int, week: int) -> int:
    """Convert ISO year/week to calendar month (1–12)."""
    try:
        return datetime.date.fromisocalendar(year, week, 1).month
    except (ValueError, AttributeError):
        return max(1, min(12, ((week - 1) // 4) + 1))


def _parse_float(value: str) -> Optional[float]:
    """Return float or None for empty/nan values."""
    if not value or value.strip().lower() in ("", "nan", "none", "null"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes")


# ─────────────────────────────────────────────────────────────────────────────
# Per-file loaders
# ─────────────────────────────────────────────────────────────────────────────

def _load_lice_csv(
    csv_path: Path,
    site_id: str,
) -> Tuple[List[LiceObservation], List[EnvironmentalObservation]]:
    """
    Read luse_historikk_{no}.csv.

    Returns
    -------
    (lice_obs, env_obs)
        lice_obs  — one LiceObservation per row with avg_adult_female_lice
        env_obs   — one EnvironmentalObservation per (year, month), aggregated
                    from weekly seaTemperature readings
    """
    lice_obs: List[LiceObservation] = []
    monthly_temps: Dict[Tuple[int, int], List[float]] = {}

    if not csv_path.exists():
        return [], []

    with open(csv_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            year_f = _parse_float(row.get("year", ""))
            week_f = _parse_float(row.get("week", ""))
            if year_f is None or week_f is None:
                continue
            year, week = int(year_f), int(week_f)
            week = max(1, min(53, week))

            avg_lice = _parse_float(row.get("avgAdultFemaleLice", "")) or 0.0
            treatment = _parse_bool(row.get("hasTreatment", "False"))

            lice_obs.append(LiceObservation(
                site_id=site_id,
                year=year,
                week=week,
                avg_lice_per_fish=avg_lice,
                treatment_applied=treatment,
            ))

            temp = _parse_float(row.get("seaTemperature", ""))
            if temp is not None:
                month = _week_to_month(year, week)
                monthly_temps.setdefault((year, month), []).append(temp)

    env_obs: List[EnvironmentalObservation] = [
        EnvironmentalObservation(
            site_id=site_id,
            year=year,
            month=month,
            sea_temp_celsius=round(sum(temps) / len(temps), 2),
        )
        for (year, month), temps in monthly_temps.items()
    ]

    return lice_obs, env_obs


def _load_sykdom_json(
    json_path: Path,
    site_id: str,
) -> List[PathogenObservation]:
    """
    Read sykdom_historikk_{no}.json.

    Maps disease records to PathogenObservation. Uses diagnosisDate if
    available (confirmed=True), otherwise suspicionDate (confirmed=False).
    """
    if not json_path.exists():
        return []

    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)

    obs: List[PathogenObservation] = []
    for tilfelle in data.get("alle_tilfeller", []):
        name = (
            tilfelle.get("name")
            or tilfelle.get("diagnosisName")
            or "ukjent"
        )
        diagnosis_date = tilfelle.get("diagnosisDate")
        suspicion_date = tilfelle.get("suspicionDate")
        date_str = diagnosis_date or suspicion_date
        confirmed = diagnosis_date is not None

        try:
            d = datetime.date.fromisoformat(date_str[:10]) if date_str else None
        except (ValueError, TypeError):
            d = None

        if d:
            year = d.year
            week = max(1, min(53, d.isocalendar()[1]))
        else:
            year = datetime.date.today().year
            week = 1

        obs.append(PathogenObservation(
            site_id=site_id,
            year=year,
            week=week,
            pathogen_type=name,
            confirmed=confirmed,
        ))

    return obs


def _load_risk_forecast_json(json_path: Path) -> dict:
    """Read risk_forecast_{no}.json and return raw dict (or empty dict)."""
    if not json_path.exists():
        return {}
    try:
        with open(json_path, encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def bw_data_available(
    data_dir: Optional[Path] = None,
    operator_cfg: Optional[dict] = None,
) -> bool:
    """
    Return True if at least one complete site dataset (CSV + sykdom JSON)
    exists in data_dir for the configured operator.
    """
    d = Path(data_dir) if data_dir else BW_DATA_DIR
    cfg = operator_cfg or DEFAULT_OPERATOR_CFG
    for loc in cfg.get("localities", []):
        no = loc["localityNo"]
        if (
            (d / f"luse_historikk_{no}.csv").exists()
            and (d / f"sykdom_historikk_{no}.json").exists()
        ):
            return True
    return False


def bw_data_to_operator_input(
    data_dir: Optional[Path] = None,
    operator_cfg: Optional[dict] = None,
) -> C5AIOperatorInput:
    """
    Build a C5AIOperatorInput from BarentsWatch output files.

    Parameters
    ----------
    data_dir : Path, optional
        Directory containing luse_historikk_{no}.csv and
        sykdom_historikk_{no}.json. Defaults to BW_DATA_DIR.
    operator_cfg : dict, optional
        Operator configuration dict. Defaults to DEFAULT_OPERATOR_CFG
        (Kornstad Havbruk AS).

    Returns
    -------
    C5AIOperatorInput
        Ready to pass to ForecastPipeline.run().
    """
    d = Path(data_dir) if data_dir else BW_DATA_DIR
    cfg = operator_cfg or DEFAULT_OPERATOR_CFG

    sites: List[SiteMetadata] = []
    all_lice: List[LiceObservation] = []
    all_env: List[EnvironmentalObservation] = []
    all_pathogen: List[PathogenObservation] = []

    for loc in cfg.get("localities", []):
        no = loc["localityNo"]
        site_id = loc["site_id"]

        sites.append(SiteMetadata(
            site_id=site_id,
            site_name=loc["site_name"],
            latitude=loc["lat"],
            longitude=loc["lon"],
            species="Atlantic Salmon",
            biomass_tonnes=loc.get("biomass_tonnes", 2000),
            biomass_value_nok=loc.get("biomass_value_nok", 130_000_000),
            fjord_exposure=loc.get("fjord_exposure", "semi_exposed"),
        ))

        lice, env = _load_lice_csv(d / f"luse_historikk_{no}.csv", site_id)
        all_lice.extend(lice)
        all_env.extend(env)

        pathogen = _load_sykdom_json(d / f"sykdom_historikk_{no}.json", site_id)
        all_pathogen.extend(pathogen)

    return C5AIOperatorInput(
        operator_id=cfg.get("operator_id", "BW_OPERATOR"),
        operator_name=cfg.get("operator_name", "BarentsWatch Operator"),
        sites=sites,
        env_observations=all_env,
        lice_observations=all_lice,
        pathogen_observations=all_pathogen,
    )


def bw_quality_summary(
    data_dir: Optional[Path] = None,
    operator_cfg: Optional[dict] = None,
) -> dict:
    """
    Return a dict summarising data quality across all localities.

    Reads risk_forecast_{no}.json metadata (data_quality_flag, reported_weeks).
    Used by the prefetch endpoint to report results.
    """
    d = Path(data_dir) if data_dir else BW_DATA_DIR
    cfg = operator_cfg or DEFAULT_OPERATOR_CFG
    sites_info = []

    for loc in cfg.get("localities", []):
        no = loc["localityNo"]
        rf = _load_risk_forecast_json(d / f"risk_forecast_{no}.json")
        meta = rf.get("metadata", {})
        agg  = rf.get("operator_aggregate", {})
        sites_info.append({
            "site_id":          loc["site_id"],
            "site_name":        loc["site_name"],
            "locality_no":      no,
            "data_quality_flag": meta.get("data_quality_flag", "UNKNOWN"),
            "reported_weeks":   meta.get("reported_weeks", 0),
            "data_weeks":       meta.get("data_weeks", 0),
            "c5ai_scale":       agg.get("c5ai_vs_static_ratio", None),
            "confidence_score": agg.get("confidence_score", None),
        })

    return {
        "operator_id":   cfg.get("operator_id"),
        "operator_name": cfg.get("operator_name"),
        "data_available": bw_data_available(d, cfg),
        "sites": sites_info,
    }

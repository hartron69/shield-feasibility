"""
C5AI+ v5.0 – Data Ingestion Layer.

Responsibilities
----------------
  – Load biological and environmental input data from dict / JSON
  – Apply data quality checks and flag missing values
  – Compute a per-site data quality score for downstream model selection
  – Provide fallback defaults when data is absent or insufficient

Design principle: Never raise on missing data; degrade gracefully and
emit warnings that propagate into the forecast metadata.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.data_models.biological_input import (
    C5AIOperatorInput,
    EnvironmentalObservation,
    HABAlert,
    JellyfishObservation,
    LiceObservation,
    PathogenObservation,
    SiteMetadata,
)


# ── Quality constants ──────────────────────────────────────────────────────────

_QUALITY_THRESHOLDS = {
    "SUFFICIENT": 0.70,   # ≥70% non-missing, ≥min_obs
    "LIMITED": 0.40,      # 40–69% coverage
    "POOR": 0.10,         # 10–39% coverage
    "PRIOR_ONLY": 0.0,    # <10% coverage → fall back to priors entirely
}


def _quality_flag(coverage: float) -> str:
    for flag, threshold in _QUALITY_THRESHOLDS.items():
        if coverage >= threshold:
            return flag
    return "PRIOR_ONLY"


# ── Site data container ────────────────────────────────────────────────────────

class SiteData:
    """
    Holds all loaded and validated data for a single site.

    Attributes
    ----------
    metadata : SiteMetadata
    env_obs : List[EnvironmentalObservation]
        Environmental observations, sorted chronologically.
    lice_obs : List[LiceObservation]
    hab_alerts : List[HABAlert]
    data_quality_flag : str
    coverage_fraction : float
        Fraction of expected monthly observations that are non-missing.
    n_obs : int
        Total number of environmental observations.
    warnings : List[str]
    """

    def __init__(
        self,
        metadata: SiteMetadata,
        env_obs: List[EnvironmentalObservation],
        lice_obs: List[LiceObservation],
        hab_alerts: List[HABAlert],
        jellyfish_obs: Optional[List[JellyfishObservation]] = None,
        pathogen_obs: Optional[List[PathogenObservation]] = None,
    ):
        self.metadata = metadata
        self.env_obs = sorted(env_obs, key=lambda o: (o.year, o.month))
        self.lice_obs = sorted(lice_obs, key=lambda o: (o.year, o.week))
        self.hab_alerts = sorted(hab_alerts, key=lambda a: (a.year, a.month))
        self.jellyfish_obs: List[JellyfishObservation] = sorted(
            jellyfish_obs or [], key=lambda o: (o.year, o.month)
        )
        self.pathogen_obs: List[PathogenObservation] = sorted(
            pathogen_obs or [], key=lambda o: (o.year, o.week)
        )
        self.warnings: List[str] = []
        self.coverage_fraction, self.n_obs = self._compute_coverage()
        self.data_quality_flag = _quality_flag(self.coverage_fraction)

    def _compute_coverage(self) -> Tuple[float, int]:
        """
        Estimate data coverage as fraction of non-missing temperature readings.
        Temperature is the primary driver for all risk models.
        """
        n_obs = len(self.env_obs)
        if n_obs == 0:
            return 0.0, 0

        n_with_temp = sum(
            1 for o in self.env_obs if o.sea_temp_celsius is not None
        )
        coverage = n_with_temp / max(n_obs, 1)

        if n_obs < C5AI_SETTINGS.min_obs_for_ml_model:
            self.warnings.append(
                f"Site '{self.metadata.site_id}': only {n_obs} observations "
                f"(need {C5AI_SETTINGS.min_obs_for_ml_model} for ML model). "
                f"Using prior distributions."
            )

        if coverage < (1 - C5AI_SETTINGS.max_missing_fraction):
            self.warnings.append(
                f"Site '{self.metadata.site_id}': {1-coverage:.0%} of temperature "
                f"readings are missing. Degraded model quality."
            )

        return coverage, n_obs

    def temperatures(self) -> np.ndarray:
        """Return array of non-null sea temperatures (Celsius)."""
        return np.array([
            o.sea_temp_celsius for o in self.env_obs
            if o.sea_temp_celsius is not None
        ], dtype=float)

    def monthly_temp_mean(self) -> Dict[int, float]:
        """Return mean temperature by calendar month (1–12)."""
        by_month: Dict[int, List[float]] = {}
        for o in self.env_obs:
            if o.sea_temp_celsius is not None:
                by_month.setdefault(o.month, []).append(o.sea_temp_celsius)
        return {m: float(np.mean(vals)) for m, vals in by_month.items()}

    def annual_hab_rate(self) -> float:
        """Historical annual HAB event rate (events per year)."""
        years_with_data = len(set(a.year for a in self.hab_alerts))
        if years_with_data == 0:
            return 0.0
        return len(self.hab_alerts) / years_with_data

    def annual_lice_exceedance_rate(self, threshold: float = 0.5) -> float:
        """
        Fraction of weekly observations where lice per fish exceeded threshold.
        Norwegian regulatory threshold = 0.5 adult female lice / fish.
        """
        if not self.lice_obs:
            return 0.0
        exceedances = sum(
            1 for o in self.lice_obs if o.avg_lice_per_fish > threshold
        )
        return exceedances / len(self.lice_obs)

    def use_ml_model(self) -> bool:
        """True if enough data exists to use a trained ML model."""
        return (
            self.n_obs >= C5AI_SETTINGS.min_obs_for_ml_model
            and self.coverage_fraction >= (1 - C5AI_SETTINGS.max_missing_fraction)
        )


# ── Loader ─────────────────────────────────────────────────────────────────────

class DataLoader:
    """
    Load and validate C5AI+ operator input data.

    Usage
    -----
    >>> loader = DataLoader()
    >>> site_data = loader.load(operator_input)
    """

    def load(self, operator_input: C5AIOperatorInput) -> Dict[str, SiteData]:
        """
        Convert a C5AIOperatorInput into a site-keyed dict of SiteData objects.

        Returns
        -------
        Dict[str, SiteData]
            Keys are site_id strings.
        """
        site_map = {s.site_id: s for s in operator_input.sites}

        env_by_site: Dict[str, List[EnvironmentalObservation]] = {
            s: [] for s in site_map
        }
        lice_by_site: Dict[str, List[LiceObservation]] = {
            s: [] for s in site_map
        }
        hab_by_site: Dict[str, List[HABAlert]] = {
            s: [] for s in site_map
        }
        jellyfish_by_site: Dict[str, List[JellyfishObservation]] = {
            s: [] for s in site_map
        }
        pathogen_by_site: Dict[str, List[PathogenObservation]] = {
            s: [] for s in site_map
        }

        for obs in operator_input.env_observations:
            if obs.site_id in env_by_site:
                env_by_site[obs.site_id].append(obs)

        for obs in operator_input.lice_observations:
            if obs.site_id in lice_by_site:
                lice_by_site[obs.site_id].append(obs)

        for alert in operator_input.hab_alerts:
            if alert.site_id in hab_by_site:
                hab_by_site[alert.site_id].append(alert)

        for obs in getattr(operator_input, "jellyfish_observations", []):
            if obs.site_id in jellyfish_by_site:
                jellyfish_by_site[obs.site_id].append(obs)

        for obs in getattr(operator_input, "pathogen_observations", []):
            if obs.site_id in pathogen_by_site:
                pathogen_by_site[obs.site_id].append(obs)

        result: Dict[str, SiteData] = {}
        for site_id, meta in site_map.items():
            result[site_id] = SiteData(
                metadata=meta,
                env_obs=env_by_site.get(site_id, []),
                lice_obs=lice_by_site.get(site_id, []),
                hab_alerts=hab_by_site.get(site_id, []),
                jellyfish_obs=jellyfish_by_site.get(site_id, []),
                pathogen_obs=pathogen_by_site.get(site_id, []),
            )

        return result

    @staticmethod
    def load_from_json(path: str) -> C5AIOperatorInput:
        """Load a C5AIOperatorInput from a JSON file."""
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return _parse_operator_input(raw)


def _parse_operator_input(raw: dict) -> C5AIOperatorInput:
    """Parse raw JSON dict into C5AIOperatorInput."""
    sites = [
        SiteMetadata(**{k: s[k] for k in SiteMetadata.__dataclass_fields__ if k in s})
        for s in raw["sites"]
    ]

    env_obs = [
        EnvironmentalObservation(
            **{k: o[k] for k in EnvironmentalObservation.__dataclass_fields__ if k in o}
        )
        for o in raw.get("env_observations", [])
    ]

    lice_obs = [
        LiceObservation(
            **{k: o[k] for k in LiceObservation.__dataclass_fields__ if k in o}
        )
        for o in raw.get("lice_observations", [])
    ]

    hab_alerts = [
        HABAlert(
            **{k: a[k] for k in HABAlert.__dataclass_fields__ if k in a}
        )
        for a in raw.get("hab_alerts", [])
    ]

    return C5AIOperatorInput(
        operator_id=raw["operator_id"],
        operator_name=raw["operator_name"],
        sites=sites,
        env_observations=env_obs,
        lice_observations=lice_obs,
        hab_alerts=hab_alerts,
        forecast_years=raw.get("forecast_years", C5AI_SETTINGS.forecast_years),
    )

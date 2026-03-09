"""
C5AI+ v5.0 – Feature Engineering.

Transforms raw biological and environmental observations into
numerical feature vectors suitable for scikit-learn estimators.

Each feature function takes a SiteData object and returns a 2-D numpy
array of shape (n_samples, n_features), along with a label array.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from c5ai_plus.ingestion.data_loader import SiteData


# ── Seasonal encoding ──────────────────────────────────────────────────────────

def _month_to_sin_cos(month: int) -> Tuple[float, float]:
    """Encode month (1–12) as sin/cos pair to capture seasonality."""
    angle = 2 * np.pi * (month - 1) / 12
    return float(np.sin(angle)), float(np.cos(angle))


# ── HAB features ───────────────────────────────────────────────────────────────

def build_hab_features(
    site_data: SiteData,
    lookback_months: int = 1,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Build feature matrix and label vector for the HAB classifier.

    Features per sample (one month of observations):
      [0] sea_temp_celsius    (or site mean if missing)
      [1] chlorophyll_ug_l    (or 0.0 if missing)
      [2] salinity_ppt        (or site mean if missing)
      [3] month_sin           (seasonal encoding)
      [4] month_cos
      [5] lag_temp_1m         (temperature previous month, or site mean)

    Label: 1 if a HAB alert was recorded in this site/month, else 0.

    Returns (X, y) or (None, None) if insufficient data.
    """
    obs = site_data.env_obs
    if len(obs) < 2:
        return None, None

    # Defaults for imputation
    temps = site_data.temperatures()
    mean_temp = float(temps.mean()) if len(temps) > 0 else 12.0
    mean_sal = 33.0  # Typical Norwegian fjord salinity

    # Build alert lookup: (year, month) → 1 if alert
    alert_months = {
        (a.year, a.month): 1
        for a in site_data.hab_alerts
    }

    rows: List[List[float]] = []
    labels: List[float] = []

    for i, o in enumerate(obs):
        temp = o.sea_temp_celsius if o.sea_temp_celsius is not None else mean_temp
        chloro = o.chlorophyll_ug_l if o.chlorophyll_ug_l is not None else 0.0
        sal = o.salinity_ppt if o.salinity_ppt is not None else mean_sal
        sin_m, cos_m = _month_to_sin_cos(o.month)

        # Lag feature: previous observation temperature
        if i > 0:
            prev = obs[i - 1]
            lag_temp = prev.sea_temp_celsius if prev.sea_temp_celsius is not None else mean_temp
        else:
            lag_temp = mean_temp

        rows.append([temp, chloro, sal, sin_m, cos_m, lag_temp])
        labels.append(float(alert_months.get((o.year, o.month), 0)))

    X = np.array(rows, dtype=float)
    y = np.array(labels, dtype=float)
    return X, y


def hab_prior_features(month: int, mean_temp: float = 12.0) -> np.ndarray:
    """
    Single-row feature vector for HAB prediction using prior assumptions.
    Used when ML model is unavailable.
    """
    sin_m, cos_m = _month_to_sin_cos(month)
    return np.array([[mean_temp, 0.0, 33.0, sin_m, cos_m, mean_temp]], dtype=float)


# ── Sea lice features ──────────────────────────────────────────────────────────

def build_lice_features(
    site_data: SiteData,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Build feature matrix and label vector for the sea lice regressor.

    Features per sample (one weekly observation):
      [0] sea_temp_celsius    (month average from env data, or prior)
      [1] avg_lice_previous   (lag-1 lice count, 0 for first record)
      [2] month_sin
      [3] month_cos
      [4] treatment_last_4wk  (1 if any treatment in past 4 weeks)

    Label: avg_lice_per_fish (continuous target for regression).

    Returns (X, y) or (None, None) if insufficient data.
    """
    lice = site_data.lice_obs
    if len(lice) < 4:
        return None, None

    # Build a month→mean temperature lookup
    monthly_temp = site_data.monthly_temp_mean()
    global_temp = float(site_data.temperatures().mean()) if len(site_data.temperatures()) > 0 else 10.0

    rows: List[List[float]] = []
    labels: List[float] = []

    for i, lo in enumerate(lice):
        # Approximate month from week number
        month = min(12, max(1, (lo.week - 1) // 4 + 1))
        temp = monthly_temp.get(month, global_temp)
        sin_m, cos_m = _month_to_sin_cos(month)

        lag_lice = lice[i - 1].avg_lice_per_fish if i > 0 else 0.0

        # Any treatment in past 4 weeks
        recent_treatment = float(
            any(lice[j].treatment_applied for j in range(max(0, i - 4), i))
        )

        rows.append([temp, lag_lice, sin_m, cos_m, recent_treatment])
        labels.append(lo.avg_lice_per_fish)

    X = np.array(rows, dtype=float)
    y = np.array(labels, dtype=float)
    return X, y


def lice_prior_features(month: int, mean_temp: float = 10.0) -> np.ndarray:
    """Single-row feature vector for lice prediction using priors."""
    sin_m, cos_m = _month_to_sin_cos(month)
    return np.array([[mean_temp, 0.3, sin_m, cos_m, 0.0]], dtype=float)

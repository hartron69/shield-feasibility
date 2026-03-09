"""
C5AI+ v5.0 – Jellyfish Risk Forecaster (Phase 2 – Temperature-Sensitive Prior).

Methodology
-----------
Rather than a flat prior, this module derives a site-specific event probability
from seasonal sea temperature data:

1. Compute the mean summer temperature (July–September, months 7–9) from
   historical EnvironmentalObservation records.  If no temperature data exists,
   fall back to the configuration default.

2. Apply a temperature-sensitivity adjustment:
   - Summer temp ≤ 12°C  → baseline prior probability (no bloom uplift)
   - Summer temp 12–16°C → linear interpolation from 0 % to +25 % uplift
   - Summer temp  > 16°C → up to +50 % uplift (capped)

3. If JellyfishObservation records are available for the site, augment the
   probability estimate using the historical density_index (observation-adjusted
   prior).  The density index is averaged across summer months and mapped to an
   additional probability modifier.

model_used values
-----------------
  "temp_adjusted_prior"         – temperature data available, no jellyfish obs
  "observation_adjusted_prior"  – jellyfish observation data also used
  "prior"                       – no site data available (config default)
"""

from __future__ import annotations

import warnings
from typing import List

import numpy as np

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.forecasting.base_forecaster import BaseForecaster
from c5ai_plus.ingestion.data_loader import SiteData


# Summer months used for jellyfish temperature analysis
_SUMMER_MONTHS = {7, 8, 9}

# Temperature thresholds for bloom probability scaling
_TEMP_LOW = 12.0   # °C – below this: no uplift
_TEMP_HIGH = 16.0  # °C – at/above this: full uplift (+50 %)
_MAX_UPLIFT = 0.50  # fractional uplift ceiling


class JellyfishForecaster(BaseForecaster):
    """
    Jellyfish risk forecaster – Phase 2 temperature-sensitive prior.

    Uses seasonal temperature modulation and optional historical
    jellyfish observation data to derive a site-specific event probability.
    No ML model is fitted (planned for Phase 3).
    """

    def __init__(self):
        super().__init__("jellyfish")

    def _fit_ml(self, site_data: SiteData) -> None:
        raise NotImplementedError(
            "Jellyfish ML model is planned for Phase 3. "
            "Falling back to temperature-adjusted prior automatically."
        )

    def _predict_ml(self, site_data: SiteData, forecast_years: int) -> List[tuple]:
        raise NotImplementedError("Phase 3 – not yet implemented.")

    def _predict_prior(
        self, site_data: SiteData, forecast_years: int
    ) -> List[tuple]:
        """
        Temperature-sensitive and observation-adjusted prior prediction.

        Returns one (prob, mean_loss, p50_loss, p90_loss) tuple per forecast year.
        """
        base_prob = C5AI_SETTINGS.jellyfish_prior_event_probability
        biomass_value = site_data.metadata.biomass_value_nok
        cv = C5AI_SETTINGS.jellyfish_loss_fraction_cv
        cond_mean = biomass_value * C5AI_SETTINGS.jellyfish_loss_fraction_mean

        # ── Step 1: summer temperature adjustment ────────────────────────────
        temp_prob, temp_model = self._temp_adjusted_prob(site_data, base_prob)

        # ── Step 2: observation adjustment ───────────────────────────────────
        obs_prob, model_used = self._observation_adjusted_prob(
            site_data, temp_prob, temp_model
        )

        # ── Step 3: compute loss quantiles ───────────────────────────────────
        p50, p90 = self._lognorm_quantiles(cond_mean, cv)
        mean_loss = obs_prob * cond_mean

        result = (obs_prob, mean_loss, obs_prob * p50, obs_prob * p90)

        # Attach model_used to the forecaster so BaseForecaster can read it.
        # We override the forecast() return by setting it here; BaseForecaster
        # uses the string returned from _fit_ml / _predict_ml paths, but for
        # prior path it uses "prior" or "prior_fallback".  We patch it at
        # the forecast() level instead (see overridden forecast() below).
        self._last_model_used = model_used

        return [result] * forecast_years

    # ── Overridden forecast() to inject custom model_used ────────────────────

    def forecast(self, site_data: SiteData, forecast_years: int):
        """
        Generate annual forecasts.  Overrides base to propagate the
        fine-grained model_used string from the prior path.
        """
        self._last_model_used = "prior"  # default; _predict_prior may update
        results = super().forecast(site_data, forecast_years)
        # Patch model_used on all returned forecasts
        model_str = getattr(self, "_last_model_used", "prior")
        for fc in results:
            fc.model_used = model_str
        return results

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _temp_adjusted_prob(
        self, site_data: SiteData, base_prob: float
    ) -> tuple[float, str]:
        """
        Adjust base probability using summer sea temperature.

        Returns (adjusted_prob, model_label).
        """
        monthly_temps = site_data.monthly_temp_mean()
        summer_temps = [
            t for m, t in monthly_temps.items() if m in _SUMMER_MONTHS
        ]

        if not summer_temps:
            return base_prob, "prior"

        summer_mean = float(np.mean(summer_temps))

        if summer_mean <= _TEMP_LOW:
            uplift = 0.0
        elif summer_mean >= _TEMP_HIGH:
            uplift = _MAX_UPLIFT
        else:
            # Linear interpolation between _TEMP_LOW and _TEMP_HIGH
            uplift = _MAX_UPLIFT * (summer_mean - _TEMP_LOW) / (_TEMP_HIGH - _TEMP_LOW)

        adjusted = min(1.0, base_prob * (1.0 + uplift))
        return round(adjusted, 4), "temp_adjusted_prior"

    def _observation_adjusted_prob(
        self, site_data: SiteData, prob: float, model_label: str
    ) -> tuple[float, str]:
        """
        Further adjust probability using historical jellyfish observations.

        The density_index (0–3) in summer months is averaged and converted to
        an additional multiplicative modifier (0 = no change, 3 = +30 % uplift).
        """
        jellyfish_obs = getattr(site_data, "jellyfish_obs", [])
        if not jellyfish_obs:
            return prob, model_label

        summer_obs = [
            o for o in jellyfish_obs if o.month in _SUMMER_MONTHS
        ]
        if not summer_obs:
            return prob, model_label

        avg_density = float(np.mean([o.density_index for o in summer_obs]))
        # density_index in [0, 3]; each unit adds +10 % to probability
        obs_uplift = avg_density * 0.10
        adjusted = min(1.0, prob * (1.0 + obs_uplift))
        return round(adjusted, 4), "observation_adjusted_prior"

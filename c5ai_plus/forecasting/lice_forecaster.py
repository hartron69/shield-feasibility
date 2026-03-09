"""
C5AI+ v5.0 – Sea Lice Risk Forecaster.

Model: RandomForestRegressor predicting avg lice per fish,
converted to a loss estimate via biomass-exposure mapping.

Norwegian regulatory threshold: 0.5 adult female lice per fish.
Exceeding this triggers mandatory treatment (cost) and can result
in forced early harvest (mortality / margin loss).

Prior (no data): Temperature-adjusted lice burden estimate using
configuration defaults.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.feature_engineering.features import build_lice_features, lice_prior_features
from c5ai_plus.forecasting.base_forecaster import BaseForecaster
from c5ai_plus.ingestion.data_loader import SiteData

try:
    from sklearn.ensemble import RandomForestRegressor
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

# Norwegian regulatory lice threshold (adult female per fish)
_LICE_REGULATORY_THRESHOLD = 0.5
# Approximate treatment cost per tonne of biomass (NOK)
_TREATMENT_COST_PER_TONNE_NOK = 4_500


class LiceForecaster(BaseForecaster):
    """Sea lice burden forecaster with treatment cost and loss estimation."""

    def __init__(self):
        super().__init__("lice")
        self._reg: Optional[object] = None

    # ── ML implementation ─────────────────────────────────────────────────────

    def _fit_ml(self, site_data: SiteData) -> None:
        if not _SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for ML forecasting.")

        X, y = build_lice_features(site_data)
        if X is None or len(X) < 8:
            raise ValueError("Insufficient lice observation data for ML training.")

        reg = RandomForestRegressor(
            n_estimators=100,
            max_depth=6,
            min_samples_leaf=3,
            random_state=42,
        )
        reg.fit(X, y)
        self._reg = reg
        self._model_fitted = True

    def _predict_ml(
        self, site_data: SiteData, forecast_years: int
    ) -> List[tuple]:
        """Predict annual mean lice burden and convert to NOK loss."""
        assert self._reg is not None

        monthly_temp = site_data.monthly_temp_mean()
        global_temp = float(site_data.temperatures().mean()) if len(site_data.temperatures()) > 0 else 10.0

        results = []
        for yr in range(forecast_years):
            monthly_burdens = []
            for month in range(1, 13):
                temp = monthly_temp.get(month, global_temp)
                X_pred = lice_prior_features(month, mean_temp=temp)
                predicted_burden = float(self._reg.predict(X_pred)[0])
                monthly_burdens.append(max(0.0, predicted_burden))

            annual_mean_burden = float(np.mean(monthly_burdens))
            prob, mean_loss, p50, p90 = self._burden_to_loss(
                site_data, annual_mean_burden
            )
            results.append((prob, mean_loss, p50, p90))

        return results

    def _predict_prior(
        self, site_data: SiteData, forecast_years: int
    ) -> List[tuple]:
        """Prior-based lice prediction from historical exceedance rate."""
        prior_prob = C5AI_SETTINGS.lice_prior_event_probability

        # Adjust using historical lice exceedance data
        if site_data.lice_obs:
            hist_exceedance = site_data.annual_lice_exceedance_rate(_LICE_REGULATORY_THRESHOLD)
            # Historical exceedance rate as fraction of weeks → annualised probability
            annual_from_hist = min(1.0, hist_exceedance * 2.0)  # conservative scaling
            prior_prob = 0.5 * prior_prob + 0.5 * annual_from_hist

        # Temperature adjustment
        temps = site_data.temperatures()
        if len(temps) > 0:
            mean_temp = float(temps.mean())
            if mean_temp > C5AI_SETTINGS.lice_temp_threshold:
                prior_prob = min(1.0, prior_prob * 1.25)

        # Representative burden for the prior scenario
        representative_burden = _LICE_REGULATORY_THRESHOLD * 1.5  # 50% above threshold

        results = []
        for _ in range(forecast_years):
            prob, mean_loss, p50, p90 = self._burden_to_loss(
                site_data, representative_burden * prior_prob
            )
            results.append((prior_prob, mean_loss, p50, p90))
        return results

    # ── Loss mapping ──────────────────────────────────────────────────────────

    def _burden_to_loss(
        self,
        site_data: SiteData,
        mean_burden: float,
    ) -> tuple:
        """
        Convert a mean annual lice burden (lice/fish) to an economic loss estimate.

        Loss components:
          1. Treatment cost = treatment_cost_per_tonne × biomass_tonnes × P(exceedance)
          2. Mortality / forced harvest loss = fraction of biomass value

        Returns (event_probability, mean_loss_nok, p50_loss_nok, p90_loss_nok).
        """
        biomass_tonnes = site_data.metadata.biomass_tonnes
        biomass_value = site_data.metadata.biomass_value_nok

        # Event probability: P(burden > threshold)
        # We model burden as LogNormal with given mean; CV from config
        cv = C5AI_SETTINGS.lice_loss_fraction_cv
        if mean_burden <= 0:
            return 0.0, 0.0, 0.0, 0.0

        sigma = np.sqrt(np.log(1 + cv ** 2))
        mu = np.log(max(mean_burden, 1e-9)) - 0.5 * sigma ** 2
        # P(burden > threshold) using log-normal CDF
        from scipy.stats import lognorm
        event_prob = float(1 - lognorm.cdf(
            _LICE_REGULATORY_THRESHOLD,
            s=sigma,
            scale=np.exp(mu),
        ))
        event_prob = float(np.clip(event_prob, 0.0, 1.0))

        # Treatment cost (conditional on exceedance)
        treatment_cost = _TREATMENT_COST_PER_TONNE_NOK * biomass_tonnes

        # Biomass loss: fraction of biomass value (conditional on event)
        biomass_loss = biomass_value * C5AI_SETTINGS.lice_loss_fraction_mean

        cond_mean_loss = treatment_cost + biomass_loss
        unconditional_mean = event_prob * cond_mean_loss

        p50, p90 = self._lognorm_quantiles(cond_mean_loss, cv)
        return (
            event_prob,
            unconditional_mean,
            event_prob * p50,
            event_prob * p90,
        )

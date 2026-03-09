"""
C5AI+ v5.0 – HAB (Harmful Algal Bloom) Risk Forecaster.

Model: RandomForestClassifier (event probability) combined with a
LogNormal loss distribution calibrated to the site's biomass value.

Prior (no data): Poisson probability from seasonal temperature profile,
defaulting to config.hab_prior_event_probability.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.feature_engineering.features import build_hab_features, hab_prior_features
from c5ai_plus.forecasting.base_forecaster import BaseForecaster
from c5ai_plus.ingestion.data_loader import SiteData

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False


class HABForecaster(BaseForecaster):
    """HAB event probability forecaster using RandomForest or prior fallback."""

    def __init__(self):
        super().__init__("hab")
        self._clf: Optional[object] = None
        self._feature_importance: Optional[np.ndarray] = None

    # ── ML implementation ─────────────────────────────────────────────────────

    def _fit_ml(self, site_data: SiteData) -> None:
        if not _SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for ML forecasting.")

        X, y = build_hab_features(site_data)
        if X is None or len(X) < 10:
            raise ValueError("Insufficient feature data for ML training.")

        # Handle class imbalance: HAB events are rare
        n_events = int(y.sum())
        if n_events == 0:
            raise ValueError("No HAB events in training data – cannot fit classifier.")

        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
        )
        clf.fit(X, y.astype(int))
        self._clf = clf
        self._feature_importance = clf.feature_importances_
        self._model_fitted = True

    def _predict_ml(
        self, site_data: SiteData, forecast_years: int
    ) -> List[tuple]:
        """
        Predict monthly HAB probability and aggregate to annual.
        Uses mean seasonal temperature from training data for future months.
        """
        assert self._clf is not None

        monthly_temp = site_data.monthly_temp_mean()
        global_temp = float(site_data.temperatures().mean()) if len(site_data.temperatures()) > 0 else 12.0

        results = []
        for yr in range(forecast_years):
            monthly_probs = []
            for month in range(1, 13):
                temp = monthly_temp.get(month, global_temp)
                X_pred = hab_prior_features(month, mean_temp=temp)
                prob_month = float(self._clf.predict_proba(X_pred)[0, 1])
                monthly_probs.append(prob_month)

            # Annual event probability: P(≥1 event) = 1 – ∏(1 – P_m)
            annual_prob = 1.0 - float(np.prod([1 - p for p in monthly_probs]))
            mean_loss, p50, p90 = self._loss_from_prob(site_data, annual_prob)
            results.append((annual_prob, mean_loss, p50, p90))

        return results

    def _predict_prior(
        self, site_data: SiteData, forecast_years: int
    ) -> List[tuple]:
        """
        Prior-based HAB prediction using configuration defaults.
        Adjusts for average temperature profile if environmental data exists.
        """
        prior_prob = C5AI_SETTINGS.hab_prior_event_probability

        # Adjust based on historical HAB rate if alerts exist
        if site_data.hab_alerts:
            historical_rate = site_data.annual_hab_rate()
            # Blend prior and historical (50/50 weight)
            prior_prob = 0.5 * prior_prob + 0.5 * min(historical_rate, 1.0)

        # Temperature adjustment: higher summer temps → higher HAB risk
        temps = site_data.temperatures()
        if len(temps) > 0:
            mean_temp = float(temps.mean())
            if mean_temp > C5AI_SETTINGS.hab_temp_threshold_high:
                prior_prob = min(1.0, prior_prob * 1.3)
            elif mean_temp < C5AI_SETTINGS.hab_temp_threshold_low:
                prior_prob = prior_prob * 0.7

        results = []
        for _ in range(forecast_years):
            mean_loss, p50, p90 = self._loss_from_prob(site_data, prior_prob)
            results.append((prior_prob, mean_loss, p50, p90))
        return results

    # ── Loss calculation ──────────────────────────────────────────────────────

    def _loss_from_prob(
        self, site_data: SiteData, event_probability: float
    ) -> tuple:
        """
        Derive expected loss distribution from event probability and biomass value.

        Loss conditional on event occurring follows LogNormal with:
          mean = hab_loss_fraction_mean × biomass_value_nok
          CV   = hab_loss_fraction_cv
        """
        biomass_value = site_data.metadata.biomass_value_nok
        cond_mean = biomass_value * C5AI_SETTINGS.hab_loss_fraction_mean
        cv = C5AI_SETTINGS.hab_loss_fraction_cv

        # Unconditional expected loss = P(event) × E[loss | event]
        unconditional_mean = event_probability * cond_mean
        p50, p90 = self._lognorm_quantiles(cond_mean, cv)

        # Unconditional P50 / P90 require simulating from Bernoulli × LogNormal
        # Approximation: scale conditional quantiles by probability
        return (
            unconditional_mean,
            event_probability * p50,
            event_probability * p90,
        )

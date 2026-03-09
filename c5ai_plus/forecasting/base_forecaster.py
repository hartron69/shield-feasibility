"""
C5AI+ v5.0 – Abstract Base Forecaster.

All risk-type forecasters inherit from BaseForecaster, which defines:
  – A standard fit/predict/forecast interface
  – Automatic fallback to prior-based prediction when data is insufficient
  – Confidence scoring based on data quality
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import numpy as np

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.data_models.forecast_schema import RiskTypeForecast
from c5ai_plus.ingestion.data_loader import SiteData


class BaseForecaster(ABC):
    """
    Abstract base class for all C5AI+ biological risk forecasters.

    Subclasses implement ``_fit_ml()``, ``_predict_ml()``, and
    ``_predict_prior()`` for their specific risk domain.

    Parameters
    ----------
    risk_type : str
        One of: "hab", "lice", "jellyfish", "pathogen".
    """

    def __init__(self, risk_type: str):
        self.risk_type = risk_type
        self._model_fitted = False
        self._training_site_data: Optional[SiteData] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def forecast(
        self,
        site_data: SiteData,
        forecast_years: int,
        model_registry=None,
    ) -> List[RiskTypeForecast]:
        """
        Generate annual forecasts for one site.

        Automatically selects ML model or prior-based prediction
        depending on data quality. Returns one RiskTypeForecast per year.

        Parameters
        ----------
        site_data : SiteData
        forecast_years : int
        model_registry : Optional[ModelRegistry]
            When provided, the Bayesian posterior from the registry is used
            to set adjusted_probability on each RiskTypeForecast. The
            event_probability field (consumed by MonteCarloEngine) is
            unchanged, preserving full backward compatibility.

        Returns
        -------
        List[RiskTypeForecast]
            One entry per forecast year (year index 1, 2, …, forecast_years).
        """
        use_ml = site_data.use_ml_model()

        if use_ml:
            try:
                self._fit_ml(site_data)
                annual_results = self._predict_ml(site_data, forecast_years)
                model_used = f"ml_{self.risk_type}"
            except Exception as exc:
                site_data.warnings.append(
                    f"ML model failed for {self.risk_type} at "
                    f"'{site_data.metadata.site_id}': {exc}. "
                    f"Falling back to prior."
                )
                annual_results = self._predict_prior(site_data, forecast_years)
                model_used = "prior_fallback"
        else:
            annual_results = self._predict_prior(site_data, forecast_years)
            model_used = "prior"

        confidence = self._confidence_score(site_data, use_ml)

        # Bayesian posterior from ModelRegistry (optional)
        posterior_prob: Optional[float] = None
        if model_registry is not None:
            try:
                operator_id = site_data.metadata.site_id.rsplit("_", 1)[0]
                prob_model = model_registry.get_probability_model(
                    operator_id, self.risk_type
                )
                posterior_prob = float(prob_model.predict())
            except Exception:
                posterior_prob = None

        forecasts = []
        for yr, (prob, mean_loss, p50_loss, p90_loss) in enumerate(annual_results, start=1):
            original_prob = float(np.clip(prob, 0.0, 1.0))
            rtf = RiskTypeForecast(
                risk_type=self.risk_type,
                year=yr,
                event_probability=original_prob,
                expected_loss_mean=float(max(mean_loss, 0.0)),
                expected_loss_p50=float(max(p50_loss, 0.0)),
                expected_loss_p90=float(max(p90_loss, 0.0)),
                confidence_score=confidence,
                data_quality_flag=site_data.data_quality_flag,
                model_used=model_used,
            )
            if posterior_prob is not None:
                rtf.baseline_probability = original_prob
                rtf.adjusted_probability = posterior_prob
            forecasts.append(rtf)
        return forecasts

    # ── Abstract methods ──────────────────────────────────────────────────────

    @abstractmethod
    def _fit_ml(self, site_data: SiteData) -> None:
        """Fit the ML model using available site data."""
        ...

    @abstractmethod
    def _predict_ml(
        self,
        site_data: SiteData,
        forecast_years: int,
    ) -> List[tuple]:
        """
        Predict using the fitted ML model.

        Returns
        -------
        List of (prob, mean_loss_nok, p50_loss_nok, p90_loss_nok) tuples,
        one per forecast year.
        """
        ...

    @abstractmethod
    def _predict_prior(
        self,
        site_data: SiteData,
        forecast_years: int,
    ) -> List[tuple]:
        """
        Predict using conservative prior distributions.

        Must handle the case of zero available data.
        Returns same format as _predict_ml.
        """
        ...

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _confidence_score(site_data: SiteData, used_ml: bool) -> float:
        """
        Compute a 0–1 confidence score.

        Higher confidence when:
          – ML model was used (vs. prior)
          – More observations are available
          – Higher data coverage fraction
        """
        base = 0.40 if used_ml else 0.20
        obs_bonus = min(0.30, site_data.n_obs / 120 * 0.30)  # up to 0.30 for 10 years
        cov_bonus = site_data.coverage_fraction * 0.30
        return round(min(1.0, base + obs_bonus + cov_bonus), 3)

    @staticmethod
    def _lognorm_quantiles(
        mean_nok: float,
        cv: float,
        q50: float = 0.50,
        q90: float = 0.90,
    ) -> tuple:
        """
        Derive P50 and P90 from a LogNormal distribution with given mean and CV.
        Returns (p50, p90) in NOK.
        """
        if mean_nok <= 0 or cv <= 0:
            return 0.0, 0.0
        sigma = np.sqrt(np.log(1 + cv ** 2))
        mu = np.log(mean_nok) - 0.5 * sigma ** 2
        p50 = float(np.exp(mu + sigma * np.sqrt(2) * 0.0))         # = exp(mu)
        p90 = float(np.exp(mu + sigma * 1.2816))                   # 90th pctl of normal
        return p50, p90

"""
RASWaterQualityForecaster

Models risk of water quality failure (O₂, CO₂, pH, temperature) in RAS facilities.
Replaces HABForecaster + JellyfishForecaster for RAS sites.

Risk type: "ras_water_quality"
Input dependencies:
  - dissolved_oxygen_mg_l (primary)
  - water_temp_c          (secondary — affects O₂ solubility)
  - nitrate_umol_l        (biofilter indicator)
  - co2_ppm               (optional)
"""

from __future__ import annotations

from typing import List, Optional

from c5ai_plus.data_models.forecast_schema import RiskTypeForecast
from c5ai_plus.data_models.smolt_biological_input import RASMonitoringData


class RASWaterQualityForecaster:
    """
    Prior-based forecaster for RAS water quality failure risk.
    Probability increases with low O₂, high temperature, and high nitrate.
    """

    RISK_TYPE = "ras_water_quality"

    # Norwegian RAS operating thresholds
    O2_CRITICAL_THRESHOLD  = 6.0    # mg/L
    O2_WARNING_THRESHOLD   = 7.5    # mg/L
    TEMP_HIGH_THRESHOLD    = 18.0   # °C (stress for salmon/trout in RAS)
    NITRATE_HIGH_THRESHOLD = 12.0   # µmol/L (biofilter load indicator)

    # Base prior: 10% annual probability for an adequately run RAS facility
    BASE_PRIOR = 0.10

    def forecast(
        self,
        site: RASMonitoringData,
        forecast_years: int = 5,
    ) -> List[RiskTypeForecast]:
        """
        Return List[RiskTypeForecast] for ras_water_quality.
        One entry per forecast year. Probability is constant across years
        (no trend model in prior-only mode).
        """
        prob, dq_flag, confidence = self._assess(site)
        results = []
        for yr in range(1, forecast_years + 1):
            results.append(RiskTypeForecast(
                risk_type            = self.RISK_TYPE,
                year                 = yr,
                event_probability    = prob,
                expected_loss_mean   = prob * self._reference_loss(site),
                expected_loss_p50    = prob * self._reference_loss(site) * 0.7,
                expected_loss_p90    = prob * self._reference_loss(site) * 1.8,
                confidence_score     = confidence,
                data_quality_flag    = dq_flag,
                model_used           = "prior",
            ))
        return results

    # ──────────────────────────────────────────────────────────────────────────

    def _assess(self, site: RASMonitoringData) -> tuple:
        """
        Returns (probability, data_quality_flag, confidence_score).
        """
        has_data = any(
            v is not None for v in (
                site.dissolved_oxygen_mg_l,
                site.water_temp_c,
                site.nitrate_umol_l,
            )
        )

        if not has_data:
            return self.BASE_PRIOR, "PRIOR_ONLY", 0.20

        prob = self.BASE_PRIOR
        n_signals = 0

        # O₂ — primary driver
        o2 = site.dissolved_oxygen_mg_l
        if o2 is not None:
            n_signals += 1
            if o2 < self.O2_CRITICAL_THRESHOLD:
                prob += 0.35
            elif o2 < self.O2_WARNING_THRESHOLD:
                prob += 0.15

        # Temperature stress
        temp = site.water_temp_c
        if temp is not None:
            n_signals += 1
            if temp > self.TEMP_HIGH_THRESHOLD:
                prob += 0.12

        # Nitrate (biofilter overload indicator)
        nitrate = site.nitrate_umol_l
        if nitrate is not None:
            n_signals += 1
            if nitrate > self.NITRATE_HIGH_THRESHOLD:
                prob += 0.10

        prob = min(prob, 1.0)
        dq_flag = "SUFFICIENT" if n_signals >= 2 else "LIMITED"
        confidence = round(0.25 + min(0.50, n_signals * 0.15), 3)
        return prob, dq_flag, confidence

    @staticmethod
    def _reference_loss(site: RASMonitoringData) -> float:
        """Approximate reference loss in NOK from biomass density."""
        if site.biomass_kg and site.biomass_kg > 0:
            return site.biomass_kg * 15.0   # ~NOK 15 per kg fish value
        return 5_000_000.0  # default NOK 5M

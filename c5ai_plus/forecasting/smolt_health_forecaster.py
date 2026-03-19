"""
SmoltHealthForecaster

Replaces PathogenForecaster for RAS smolt.
Models health events specific to the RAS environment:
  - Cataract (eye damage from excessive CO₂)
  - AGD (amoebic gill disease — occurs in RAS)
  - Bacterial infection (Flavobacterium, Yersinia)

Risk type: "smolt_health"
Input dependencies:
  - cataract_prevalence_pct (primary)
  - agd_score_mean          (primary)
  - mortality_rate_7d_pct   (direct health indicator)
  - co2_ppm                 (CO₂-related cataract driver)
  - stocking_density_kg_m3  (crowding → disease transmission)
"""

from __future__ import annotations

from typing import List

from c5ai_plus.data_models.forecast_schema import RiskTypeForecast
from c5ai_plus.data_models.smolt_biological_input import RASMonitoringData


class SmoltHealthForecaster:
    """
    Prior-based forecaster for smolt health events in RAS facilities.
    """

    RISK_TYPE = "smolt_health"

    CATARACT_THRESHOLD        = 5.0    # % prevalence
    AGD_SCORE_THRESHOLD       = 1.5    # mean gill score (0–4 scale)
    MORTALITY_7D_THRESHOLD    = 0.5    # % per week
    CO2_HIGH_THRESHOLD        = 15.0   # ppm (above comfort zone)
    STOCKING_HIGH_THRESHOLD   = 80.0   # kg/m³

    BASE_PRIOR = 0.08

    def forecast(
        self,
        site: RASMonitoringData,
        forecast_years: int = 5,
    ) -> List[RiskTypeForecast]:
        prob, dq_flag, confidence = self._assess(site)
        ref_loss = self._reference_loss(site)
        results = []
        for yr in range(1, forecast_years + 1):
            results.append(RiskTypeForecast(
                risk_type         = self.RISK_TYPE,
                year              = yr,
                event_probability = prob,
                expected_loss_mean= prob * ref_loss,
                expected_loss_p50 = prob * ref_loss * 0.60,
                expected_loss_p90 = prob * ref_loss * 1.9,
                confidence_score  = confidence,
                data_quality_flag = dq_flag,
                model_used        = "prior",
            ))
        return results

    def _assess(self, site: RASMonitoringData) -> tuple:
        has_data = any(
            v is not None for v in (
                site.cataract_prevalence_pct,
                site.agd_score_mean,
                site.mortality_rate_7d_pct,
                site.co2_ppm,
                site.stocking_density_kg_m3,
            )
        )
        if not has_data:
            return self.BASE_PRIOR, "PRIOR_ONLY", 0.20

        prob = self.BASE_PRIOR
        n_signals = 0

        if site.cataract_prevalence_pct is not None:
            n_signals += 1
            if site.cataract_prevalence_pct > self.CATARACT_THRESHOLD:
                prob += 0.25

        if site.agd_score_mean is not None:
            n_signals += 1
            if site.agd_score_mean > self.AGD_SCORE_THRESHOLD:
                prob += 0.20

        if site.mortality_rate_7d_pct is not None:
            n_signals += 1
            if site.mortality_rate_7d_pct > self.MORTALITY_7D_THRESHOLD:
                prob += 0.30

        if site.co2_ppm is not None:
            n_signals += 1
            if site.co2_ppm > self.CO2_HIGH_THRESHOLD:
                prob += 0.15

        if site.stocking_density_kg_m3 is not None:
            n_signals += 1
            if site.stocking_density_kg_m3 > self.STOCKING_HIGH_THRESHOLD:
                prob += 0.10

        prob = min(prob, 1.0)
        dq_flag = "SUFFICIENT" if n_signals >= 2 else "LIMITED"
        confidence = round(0.25 + min(0.50, n_signals * 0.10), 3)
        return prob, dq_flag, confidence

    @staticmethod
    def _reference_loss(site: RASMonitoringData) -> float:
        if site.biomass_kg and site.biomass_kg > 0:
            return site.biomass_kg * 12.0
        return 4_000_000.0

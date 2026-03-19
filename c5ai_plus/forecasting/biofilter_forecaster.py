"""
BiofilterForecaster

Models risk of biofilter failure in RAS systems.
Biofilter is the single most critical component in RAS — failure leads to rapid
ammonium/nitrite accumulation and potentially total generation loss.

Risk type: "biofilter"
Input dependencies:
  - nitrite_mg_l                       (primary)
  - ammonia_mg_l                       (primary)
  - nitrate_umol_l                     (secondary)
  - days_since_last_filter_maintenance (operational)
  - biofilter_efficiency_pct           (direct indicator)
"""

from __future__ import annotations

from typing import List

from c5ai_plus.data_models.forecast_schema import RiskTypeForecast
from c5ai_plus.data_models.smolt_biological_input import RASMonitoringData


class BiofilterForecaster:
    """
    Prior-based forecaster for RAS biofilter failure risk.
    Risk increases with elevated nitrite/ammonia, overdue maintenance,
    and low biofilter efficiency.
    """

    RISK_TYPE = "biofilter"

    NITRITE_THRESHOLD            = 0.1    # mg/L — stress threshold
    AMMONIA_THRESHOLD            = 0.5    # mg/L — total ammonia nitrogen
    NITRATE_HIGH_THRESHOLD       = 12.0   # µmol/L
    MAINTENANCE_OVERDUE_DAYS     = 90     # days without maintenance
    EFFICIENCY_LOW_THRESHOLD     = 80.0   # %

    BASE_PRIOR = 0.12

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
                expected_loss_p50 = prob * ref_loss * 0.65,
                expected_loss_p90 = prob * ref_loss * 2.0,
                confidence_score  = confidence,
                data_quality_flag = dq_flag,
                model_used        = "prior",
            ))
        return results

    def _assess(self, site: RASMonitoringData) -> tuple:
        has_data = any(
            v is not None for v in (
                site.nitrite_mg_l,
                site.ammonia_mg_l,
                site.days_since_last_filter_maintenance,
                site.biofilter_efficiency_pct,
            )
        )
        if not has_data:
            return self.BASE_PRIOR, "PRIOR_ONLY", 0.20

        prob = self.BASE_PRIOR
        n_signals = 0

        if site.nitrite_mg_l is not None:
            n_signals += 1
            if site.nitrite_mg_l > self.NITRITE_THRESHOLD:
                prob += 0.25

        if site.ammonia_mg_l is not None:
            n_signals += 1
            if site.ammonia_mg_l > self.AMMONIA_THRESHOLD:
                prob += 0.20

        if site.days_since_last_filter_maintenance is not None:
            n_signals += 1
            if site.days_since_last_filter_maintenance > self.MAINTENANCE_OVERDUE_DAYS:
                prob += 0.25

        if site.biofilter_efficiency_pct is not None:
            n_signals += 1
            if site.biofilter_efficiency_pct < self.EFFICIENCY_LOW_THRESHOLD:
                prob += 0.20

        if site.nitrate_umol_l is not None:
            n_signals += 1
            if site.nitrate_umol_l > self.NITRATE_HIGH_THRESHOLD:
                prob += 0.10

        prob = min(prob, 1.0)
        dq_flag = "SUFFICIENT" if n_signals >= 3 else "LIMITED"
        confidence = round(0.25 + min(0.50, n_signals * 0.10), 3)
        return prob, dq_flag, confidence

    @staticmethod
    def _reference_loss(site: RASMonitoringData) -> float:
        if site.biomass_kg and site.biomass_kg > 0:
            return site.biomass_kg * 18.0   # total generation loss scenario
        return 8_000_000.0

"""
PowerSupplyForecaster

No sea-farming equivalent — unique to RAS.
Models power outage risk × backup capacity.
Critical for RAS: without circulation, O₂ collapses in < 30 minutes.

Risk type: "power_supply"
Input dependencies:
  - backup_power_hours    (UPS + generator capacity)
  - grid_reliability_score (local grid supplier, 0–1)
  - last_power_test_days  (days since last backup test)
"""

from __future__ import annotations

from typing import List

from c5ai_plus.data_models.forecast_schema import RiskTypeForecast
from c5ai_plus.data_models.smolt_biological_input import RASMonitoringData


class PowerSupplyForecaster:
    """
    Prior-based forecaster for power supply failure risk in RAS facilities.
    Risk is driven by backup capacity, grid reliability, and test recency.
    """

    RISK_TYPE = "power_supply"

    BACKUP_MINIMUM_HOURS       = 4.0    # hours — minimum adequate backup
    GRID_RELIABILITY_THRESHOLD = 0.85   # below this = elevated risk
    POWER_TEST_OVERDUE_DAYS    = 30     # days — test should be recent

    BASE_PRIOR = 0.05   # Low base probability for well-run facility

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
                expected_loss_p50 = prob * ref_loss * 0.55,
                expected_loss_p90 = prob * ref_loss * 2.2,
                confidence_score  = confidence,
                data_quality_flag = dq_flag,
                model_used        = "prior",
            ))
        return results

    def _assess(self, site: RASMonitoringData) -> tuple:
        has_data = any(
            v is not None for v in (
                site.backup_power_hours,
                site.grid_reliability_score,
                site.last_power_test_days,
            )
        )
        if not has_data:
            return self.BASE_PRIOR, "PRIOR_ONLY", 0.20

        prob = self.BASE_PRIOR
        n_signals = 0

        if site.backup_power_hours is not None:
            n_signals += 1
            if site.backup_power_hours < self.BACKUP_MINIMUM_HOURS:
                prob += 0.30   # Critical: inadequate backup

        if site.grid_reliability_score is not None:
            n_signals += 1
            if site.grid_reliability_score < self.GRID_RELIABILITY_THRESHOLD:
                prob += 0.20

        if site.last_power_test_days is not None:
            n_signals += 1
            if site.last_power_test_days > self.POWER_TEST_OVERDUE_DAYS:
                prob += 0.15

        prob = min(prob, 1.0)
        dq_flag = "SUFFICIENT" if n_signals >= 2 else "LIMITED"
        confidence = round(0.25 + min(0.50, n_signals * 0.17), 3)
        return prob, dq_flag, confidence

    @staticmethod
    def _reference_loss(site: RASMonitoringData) -> float:
        """Power outage can destroy entire standing biomass + BI trigger."""
        if site.biomass_kg and site.biomass_kg > 0:
            return site.biomass_kg * 20.0
        return 10_000_000.0

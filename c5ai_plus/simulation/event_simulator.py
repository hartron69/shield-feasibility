"""
C5AI+ v5.0 – Event Simulator.

Generates plausible ObservedEvent instances from a RiskForecast.

Domain logic:
  - event_occurred ~ Bernoulli(event_probability)
  - loss ~ LogNormal(mean=expected_loss_mean) when event occurs, 0 otherwise
  - Cross-risk correlation: HAB occurrence slightly elevates other bio events
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional

from c5ai_plus.data_models.forecast_schema import RiskForecast
from c5ai_plus.data_models.learning_schema import ObservedEvent


class EventSimulator:
    """
    Simulate observed outcomes for one or more forecast years.

    Parameters
    ----------
    seed : int
        Random seed for reproducibility.
    """

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    # ── Public API ─────────────────────────────────────────────────────────

    def simulate_year(
        self,
        forecast: RiskForecast,
        forecast_year: int,
        operator_id: str,
        year_offset: int = 1,
    ) -> List[ObservedEvent]:
        """
        Draw one realisation of events for a single forecast year.

        Parameters
        ----------
        forecast : RiskForecast
            The C5AI+ output to simulate against.
        forecast_year : int
            Calendar year being simulated (stored in event_year).
        operator_id : str
        year_offset : int
            Which forecast year index (1-indexed) to use from site_forecasts.

        Returns
        -------
        List[ObservedEvent]
            One ObservedEvent per (site, risk_type).
        """
        events: List[ObservedEvent] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # First pass: determine HAB events (used for cross-risk correlation)
        hab_sites: set = set()
        site_rtf_map = {}
        for sf in forecast.site_forecasts:
            for rtf in sf.annual_forecasts:
                if rtf.year == year_offset:
                    site_rtf_map.setdefault(sf.site_id, {})[rtf.risk_type] = rtf
                    if rtf.risk_type == "hab":
                        p_hab = float(rtf.event_probability)
                        if self._rng.random() < p_hab:
                            hab_sites.add(sf.site_id)

        for sf in forecast.site_forecasts:
            rtf_by_type = site_rtf_map.get(sf.site_id, {})
            hab_occurred = sf.site_id in hab_sites

            for risk_type, rtf in rtf_by_type.items():
                p = float(rtf.event_probability)

                # Cross-risk: HAB elevates other biological risks slightly
                if hab_occurred and risk_type != "hab":
                    p = min(1.0, p * 1.15)

                # HAB was pre-determined in first pass
                if risk_type == "hab":
                    occurred = hab_occurred
                else:
                    occurred = self._rng.random() < p

                # Loss amount
                if occurred and rtf.expected_loss_mean > 0:
                    loss_nok = self._sample_lognormal(rtf.expected_loss_mean, cv=0.60)
                else:
                    loss_nok = 0.0

                events.append(
                    ObservedEvent(
                        operator_id=operator_id,
                        site_id=sf.site_id,
                        risk_type=risk_type,
                        event_year=forecast_year,
                        observed_at=now_iso,
                        event_occurred=occurred,
                        actual_loss_nok=loss_nok,
                        source="simulated",
                    )
                )

        return events

    def simulate_multi_year(
        self,
        forecast: RiskForecast,
        start_year: int,
        n_years: int,
        operator_id: str,
    ) -> Dict[int, List[ObservedEvent]]:
        """
        Simulate events across multiple years.

        Uses forecast year 1 for all years (single-year forecast held constant).

        Returns
        -------
        Dict[calendar_year → List[ObservedEvent]]
        """
        result: Dict[int, List[ObservedEvent]] = {}
        for i in range(n_years):
            year = start_year + i
            # Cycle through forecast years 1..forecast_years
            year_offset = (i % forecast.metadata.forecast_horizon_years) + 1
            result[year] = self.simulate_year(
                forecast, forecast_year=year,
                operator_id=operator_id,
                year_offset=year_offset,
            )
        return result

    # ── Helpers ────────────────────────────────────────────────────────────

    def _sample_lognormal(self, mean: float, cv: float) -> float:
        """Sample from LogNormal with given mean and coefficient of variation."""
        if mean <= 0 or cv <= 0:
            return 0.0
        sigma2 = math.log(1 + cv ** 2)
        mu = math.log(mean) - 0.5 * sigma2
        log_val = self._rng.gauss(mu, math.sqrt(sigma2))
        return max(0.0, math.exp(log_val))

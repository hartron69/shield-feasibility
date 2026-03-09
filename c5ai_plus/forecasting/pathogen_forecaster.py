"""
C5AI+ v5.0 – Pathogen Risk Forecaster (Phase 2 – Network Contagion Model).

Covers bacterial (Moritella viscosa, Aeromonas salmonicida) and viral
(ILA / ISA, PD / SAV) pathogens affecting Norwegian salmon farming.

Methodology
-----------
Three adjustable risk factors combine multiplicatively on the base prior:

1. **Lice pressure proxy** – High sea lice burdens weaken fish immune systems.
   The annual lice exceedance rate (fraction of weeks above 0.5 lice/fish) is
   used as a proxy for immune suppression:
     pressure_multiplier = 1 + exceedance_rate * 0.5   (capped at 1.5)

2. **Treatment-resistance signal** – Frequent treatment applications with no
   resolution indicate a chronic disease-pressure environment.  Each treatment
   week where lice still exceeded threshold adds to a resistance score.

3. **Network contagion multiplier** – Sites connected to neighbours with high
   risk scores (via SiteRiskNetwork) face elevated ILA/PD spread risk.
   get_risk_multiplier() returns ≥ 1.0 based on weighted neighbour connections.

4. **Observation adjustment** – If PathogenObservation records are available,
   historical outbreak frequency and confirmed mortality rates are used to
   override the prior directly.

model_used values
-----------------
  "network_prior"              – network multiplier applied, no obs data
  "treatment_adjusted_prior"   – treatment history used, no obs data
  "observation_based"          – historical pathogen obs used
  "prior"                      – no site data; config default only
"""

from __future__ import annotations

import warnings
from typing import List, Optional

import numpy as np

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.forecasting.base_forecaster import BaseForecaster
from c5ai_plus.ingestion.data_loader import SiteData
from c5ai_plus.network.site_network import SiteRiskNetwork


# Maximum multiplier from any single risk factor
_MAX_SINGLE_FACTOR = 1.5
# Combined ceiling (product of all factors)
_MAX_COMBINED_MULTIPLIER = 2.5


class PathogenForecaster(BaseForecaster):
    """
    Pathogen risk forecaster – Phase 2 network contagion model.

    Parameters
    ----------
    network : Optional[SiteRiskNetwork]
        Pre-built site risk network.  If None a network is not used and the
        network multiplier defaults to 1.0.
    """

    def __init__(self, network: Optional[SiteRiskNetwork] = None):
        super().__init__("pathogen")
        self._network = network

    def _fit_ml(self, site_data: SiteData) -> None:
        raise NotImplementedError(
            "Pathogen ML model is planned for Phase 3. "
            "Falling back to network contagion prior automatically."
        )

    def _predict_ml(self, site_data: SiteData, forecast_years: int) -> List[tuple]:
        raise NotImplementedError("Phase 3 – not yet implemented.")

    def _predict_prior(
        self, site_data: SiteData, forecast_years: int
    ) -> List[tuple]:
        """
        Network- and treatment-adjusted prior prediction.

        Returns one (prob, mean_loss, p50_loss, p90_loss) tuple per year.
        """
        base_prob = C5AI_SETTINGS.pathogen_prior_event_probability
        biomass_value = site_data.metadata.biomass_value_nok
        cv = C5AI_SETTINGS.pathogen_loss_fraction_cv
        cond_mean = biomass_value * C5AI_SETTINGS.pathogen_loss_fraction_mean

        # ── Step 1: check for historical pathogen observations ────────────────
        obs_result = self._observation_based_prob(site_data, biomass_value, cv)
        if obs_result is not None:
            self._last_model_used = "observation_based"
            return [obs_result] * forecast_years

        # ── Step 2: lice pressure multiplier ─────────────────────────────────
        lice_multiplier, treatment_flag = self._lice_pressure_multiplier(site_data)

        # ── Step 3: network contagion multiplier ──────────────────────────────
        network_multiplier = self._network_multiplier(site_data.metadata.site_id)

        # ── Step 4: combine factors ───────────────────────────────────────────
        combined = min(
            _MAX_COMBINED_MULTIPLIER,
            lice_multiplier * network_multiplier
        )
        adjusted_prob = min(1.0, base_prob * combined)

        if treatment_flag and network_multiplier > 1.0:
            self._last_model_used = "network_prior"
        elif treatment_flag:
            self._last_model_used = "treatment_adjusted_prior"
        elif network_multiplier > 1.0:
            self._last_model_used = "network_prior"
        else:
            self._last_model_used = "prior"

        p50, p90 = self._lognorm_quantiles(cond_mean, cv)
        mean_loss = adjusted_prob * cond_mean
        result = (adjusted_prob, mean_loss, adjusted_prob * p50, adjusted_prob * p90)
        return [result] * forecast_years

    # ── Overridden forecast() to inject custom model_used ────────────────────

    def forecast(self, site_data: SiteData, forecast_years: int):
        """
        Generate annual forecasts.  Overrides base to propagate the
        fine-grained model_used string from the prior path.
        """
        self._last_model_used = "prior"
        results = super().forecast(site_data, forecast_years)
        model_str = getattr(self, "_last_model_used", "prior")
        for fc in results:
            fc.model_used = model_str
        return results

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _lice_pressure_multiplier(self, site_data: SiteData) -> tuple[float, bool]:
        """
        Derive a multiplier from lice exceedance rate and treatment history.

        Returns (multiplier, treatment_flag).
        """
        exceedance = site_data.annual_lice_exceedance_rate()
        if exceedance == 0.0:
            return 1.0, False

        # Exceedance rate contributes up to +50 % uplift
        pressure_multiplier = min(_MAX_SINGLE_FACTOR, 1.0 + exceedance * 0.5)

        # Treatment history: count treatment weeks where lice still exceeded
        treatment_flag = False
        if site_data.lice_obs:
            treated_weeks = [
                o for o in site_data.lice_obs
                if o.treatment_applied and o.avg_lice_per_fish > 0.5
            ]
            if len(treated_weeks) > 4:
                # Chronic unresolved lice pressure → additional +10 %
                pressure_multiplier = min(_MAX_SINGLE_FACTOR, pressure_multiplier * 1.10)
                treatment_flag = True

        return round(pressure_multiplier, 4), treatment_flag

    def _network_multiplier(self, site_id: str) -> float:
        """Return the network-based risk multiplier for this site."""
        if self._network is None:
            return 1.0
        return self._network.get_risk_multiplier(site_id)

    def _observation_based_prob(
        self, site_data: SiteData, biomass_value: float, cv: float
    ) -> Optional[tuple]:
        """
        If PathogenObservation records exist, derive probability directly
        from historical outbreak frequency and confirmed mortality rates.

        Returns a (prob, mean_loss, p50, p90) tuple or None.
        """
        pathogen_obs = getattr(site_data, "pathogen_obs", [])
        if not pathogen_obs:
            return None

        # Count confirmed outbreak-years
        confirmed_obs = [o for o in pathogen_obs if o.confirmed]
        if not confirmed_obs:
            return None

        outbreak_years = len(set(o.year for o in confirmed_obs))
        total_years = max(
            len(set(o.year for o in pathogen_obs)),
            1
        )
        historical_rate = min(1.0, outbreak_years / total_years)

        # Mean mortality fraction from confirmed outbreaks
        mortality_rates = [
            o.mortality_rate for o in confirmed_obs
            if o.mortality_rate is not None
        ]
        if mortality_rates:
            mean_mortality = float(np.mean(mortality_rates))
        else:
            mean_mortality = C5AI_SETTINGS.pathogen_loss_fraction_mean

        # Combine historical outbreak rate with network multiplier for forward
        # projection (network contagion still relevant even with obs data)
        network_mult = self._network_multiplier(site_data.metadata.site_id)
        adjusted_prob = min(1.0, historical_rate * min(network_mult, 1.25))

        cond_mean = biomass_value * mean_mortality
        p50, p90 = self._lognorm_quantiles(cond_mean, cv)
        mean_loss = adjusted_prob * cond_mean
        return (adjusted_prob, mean_loss, adjusted_prob * p50, adjusted_prob * p90)

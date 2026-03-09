"""
Shield Captive Risk Platform – Biological Risk Domain.

Wrapper that runs the four C5AI+ biological forecasters (HAB, lice,
jellyfish, pathogen) and normalises their outputs into DomainRiskSummary
objects for consumption by the unified risk architecture.
"""

from __future__ import annotations

from typing import List, Optional

from risk_domains.base_domain import DomainRiskSummary, RiskDomain
from c5ai_plus.ingestion.data_loader import SiteData


class BiologicalRiskDomain(RiskDomain):
    """
    Biological risk domain – backed by C5AI+ forecasters.

    Parameters
    ----------
    forecast_years : int
        Number of years to forecast (default 5).
    network : optional SiteRiskNetwork
        Passed to PathogenForecaster for contagion modelling.
    """

    domain_name = "biological"

    def __init__(self, forecast_years: int = 5, network=None):
        self.forecast_years = forecast_years
        self._network = network

    def assess(self, site_data: SiteData) -> List[DomainRiskSummary]:
        """
        Run all four biological forecasters for one site and return
        a DomainRiskSummary per risk sub-type.

        The summary uses Year-1 forecast values as the representative
        annual estimate (Year 1 is identical across prior-based forecasters).
        """
        from c5ai_plus.forecasting.hab_forecaster import HABForecaster
        from c5ai_plus.forecasting.lice_forecaster import LiceForecaster
        from c5ai_plus.forecasting.jellyfish_forecaster import JellyfishForecaster
        from c5ai_plus.forecasting.pathogen_forecaster import PathogenForecaster

        forecasters = [
            ("hab", HABForecaster()),
            ("lice", LiceForecaster()),
            ("jellyfish", JellyfishForecaster()),
            ("pathogen", PathogenForecaster(network=self._network)),
        ]

        summaries: List[DomainRiskSummary] = []
        for sub_type, forecaster in forecasters:
            try:
                forecasts = forecaster.forecast(site_data, self.forecast_years)
                if not forecasts:
                    continue
                yr1 = forecasts[0]
                summaries.append(DomainRiskSummary(
                    domain=self.domain_name,
                    sub_type=sub_type,
                    event_probability=yr1.event_probability,
                    expected_annual_loss_nok=yr1.expected_loss_mean,
                    model_type=yr1.model_used,
                    confidence=yr1.confidence_score,
                    data_quality=yr1.data_quality_flag,
                    metadata={
                        "p50_loss_nok": yr1.expected_loss_p50,
                        "p90_loss_nok": yr1.expected_loss_p90,
                        "site_id": site_data.metadata.site_id,
                    },
                ))
            except Exception as exc:
                summaries.append(DomainRiskSummary(
                    domain=self.domain_name,
                    sub_type=sub_type,
                    event_probability=0.0,
                    expected_annual_loss_nok=0.0,
                    model_type="stub",
                    confidence=0.0,
                    data_quality="PRIOR_ONLY",
                    metadata={"error": str(exc)},
                ))

        return summaries

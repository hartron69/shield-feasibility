"""
C5AI+ v5.0 – Main Forecasting Pipeline.

Orchestrates all C5AI+ components in sequence:

  1. Load and validate biological input data
  2. Build site risk network
  3. Run per-site forecasters (HAB, lice, jellyfish, pathogen)
  4. Apply network risk multipliers
  5. Aggregate to operator level
  6. Export to risk_forecast.json

Usage (standalone)
------------------
    python -m c5ai_plus.pipeline --input c5ai_input.json --output risk_forecast.json

Usage (programmatic)
--------------------
    from c5ai_plus.pipeline import ForecastPipeline
    from c5ai_plus.data_models.biological_input import C5AIOperatorInput

    pipeline = ForecastPipeline()
    forecast = pipeline.run(operator_input, static_mean_annual_loss=22_600_000)
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from c5ai_plus.config.c5ai_settings import C5AI_SETTINGS
from c5ai_plus.data_models.biological_input import C5AIOperatorInput
from c5ai_plus.data_models.forecast_schema import (
    ForecastMetadata,
    OperatorAggregate,
    RiskForecast,
    RiskTypeForecast,
    SiteForecast,
    RISK_TYPES,
)
from c5ai_plus.export.forecast_exporter import ForecastExporter
from c5ai_plus.forecasting.hab_forecaster import HABForecaster
from c5ai_plus.forecasting.jellyfish_forecaster import JellyfishForecaster
from c5ai_plus.forecasting.lice_forecaster import LiceForecaster
from c5ai_plus.forecasting.pathogen_forecaster import PathogenForecaster
from c5ai_plus.ingestion.data_loader import DataLoader, SiteData
from c5ai_plus.network.site_network import SiteRiskNetwork
from c5ai_plus.validation.forecast_validator import ForecastValidator


class ForecastPipeline:
    """
    End-to-end C5AI+ forecasting pipeline.

    Parameters
    ----------
    verbose : bool
        Print progress messages if True.
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self._loader = DataLoader()
        self._validator = ForecastValidator()
        self._forecasters = {
            "hab": HABForecaster(),
            "lice": LiceForecaster(),
            "jellyfish": JellyfishForecaster(),
            "pathogen": PathogenForecaster(),
        }

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [C5AI+] {msg}", flush=True)

    def run(
        self,
        operator_input: C5AIOperatorInput,
        static_mean_annual_loss: float,
        output_path: Optional[str] = None,
    ) -> RiskForecast:
        """
        Execute the full pipeline.

        Parameters
        ----------
        operator_input : C5AIOperatorInput
            Biological and environmental data for the operator.
        static_mean_annual_loss : float
            The static Monte Carlo model's E[annual loss] in NOK.
            Used to compute c5ai_vs_static_ratio.
        output_path : Optional[str]
            If provided, write risk_forecast.json to this path.

        Returns
        -------
        RiskForecast
        """
        forecast_years = operator_input.forecast_years
        all_warnings: List[str] = []

        # ── Step 1: Load and validate site data ────────────────────────────
        self._log("Loading biological input data...")
        site_data_map: Dict[str, SiteData] = self._loader.load(operator_input)

        # ── Step 2: Build site risk network ────────────────────────────────
        self._log("Building site risk network...")
        network = SiteRiskNetwork(operator_input.sites)
        net_summary = network.network_summary()
        if net_summary.get("available"):
            self._log(
                f"Network: {net_summary['n_sites']} sites, "
                f"{net_summary['n_connections']} connections."
            )
        else:
            all_warnings.append(
                "networkx not installed – site risk network disabled. "
                "Install with: pip install networkx"
            )

        # ── Step 3: Run per-site forecasters ───────────────────────────────
        self._log("Running per-site risk forecasters...")
        site_forecasts: List[SiteForecast] = []
        all_site_quality_flags: List[str] = []

        for site_id, site_data in site_data_map.items():
            self._log(
                f"  Site '{site_data.metadata.site_name}' "
                f"[quality={site_data.data_quality_flag}, n_obs={site_data.n_obs}]"
            )
            all_warnings.extend(site_data.warnings)

            # Network risk multiplier for this site
            net_multiplier = network.get_risk_multiplier(site_id)
            if net_multiplier > 1.0:
                self._log(
                    f"    Network risk multiplier: {net_multiplier:.3f} "
                    f"({network.connected_sites(site_id)} connected neighbours)"
                )

            # Run each forecaster
            site_annual_forecasts: List[RiskTypeForecast] = []
            for risk_type, forecaster in self._forecasters.items():
                rtf_list = forecaster.forecast(site_data, forecast_years)
                # Apply network multiplier to loss estimates
                if net_multiplier > 1.0:
                    rtf_list = [
                        RiskTypeForecast(
                            risk_type=rtf.risk_type,
                            year=rtf.year,
                            event_probability=min(1.0, rtf.event_probability * net_multiplier),
                            expected_loss_mean=rtf.expected_loss_mean * net_multiplier,
                            expected_loss_p50=rtf.expected_loss_p50 * net_multiplier,
                            expected_loss_p90=rtf.expected_loss_p90 * net_multiplier,
                            confidence_score=rtf.confidence_score,
                            data_quality_flag=rtf.data_quality_flag,
                            model_used=rtf.model_used,
                        )
                        for rtf in rtf_list
                    ]
                site_annual_forecasts.extend(rtf_list)

            site_forecasts.append(
                SiteForecast(
                    site_id=site_id,
                    site_name=site_data.metadata.site_name,
                    annual_forecasts=site_annual_forecasts,
                )
            )
            all_site_quality_flags.append(site_data.data_quality_flag)

        # ── Step 4: Build operator aggregate ───────────────────────────────
        self._log("Computing operator-level aggregates...")
        aggregate = self._build_aggregate(
            site_forecasts, static_mean_annual_loss, forecast_years
        )

        # ── Step 5: Assemble metadata ──────────────────────────────────────
        overall_quality = self._overall_quality(all_site_quality_flags)
        confidence_label = self._confidence_label(all_site_quality_flags)

        metadata = ForecastMetadata(
            model_version=C5AI_SETTINGS.model_version,
            generated_at=datetime.now(timezone.utc).isoformat(),
            operator_id=operator_input.operator_id,
            operator_name=operator_input.operator_name,
            forecast_horizon_years=forecast_years,
            overall_confidence=confidence_label,
            overall_data_quality=overall_quality,
            sites_included=[sf.site_id for sf in site_forecasts],
            warnings=all_warnings,
        )

        # ── Step 6: Assemble and validate forecast ─────────────────────────
        forecast = RiskForecast(
            metadata=metadata,
            site_forecasts=site_forecasts,
            operator_aggregate=aggregate,
        )

        validation_errors = self._validator.validate(forecast)
        if validation_errors:
            all_warnings.extend([f"VALIDATION WARNING: {e}" for e in validation_errors])

        # ── Step 7: Export ─────────────────────────────────────────────────
        if output_path:
            exporter = ForecastExporter(output_path)
            written_path = exporter.export(forecast)
            self._log(f"Forecast written to: {written_path}")

        self._log(
            f"Done. C5AI+ scale factor vs. static model: "
            f"{aggregate.c5ai_vs_static_ratio:.3f} | "
            f"Total E[annual loss]: NOK {aggregate.total_expected_annual_loss/1e6:,.1f} M"
        )

        return forecast

    # ── Aggregation helpers ───────────────────────────────────────────────────

    def _build_aggregate(
        self,
        site_forecasts: List[SiteForecast],
        static_mean_annual_loss: float,
        forecast_years: int,
    ) -> OperatorAggregate:
        """
        Aggregate site-level forecasts to operator level.

        Computes:
          – Mean annual expected loss per risk type (averaged across years)
          – Total expected annual loss
          – Scale factor vs. static model
          – Loss breakdown fractions
        """
        # Sum expected losses per risk type across all sites and years
        loss_by_type: Dict[str, List[float]] = {rt: [] for rt in RISK_TYPES}

        for sf in site_forecasts:
            for yr in range(1, forecast_years + 1):
                for rt in RISK_TYPES:
                    rtf = sf.get_forecast(rt, yr)
                    if rtf is not None:
                        loss_by_type[rt].append(rtf.expected_loss_mean)

        # Annual mean per risk type (sum over sites, mean over years)
        annual_by_type: Dict[str, float] = {}
        for rt in RISK_TYPES:
            vals = loss_by_type[rt]
            if vals:
                # Sum across sites in each year, then mean across years
                # (simplified: vals already contains per-site-per-year figures)
                annual_by_type[rt] = float(np.sum(vals) / forecast_years)
            else:
                annual_by_type[rt] = 0.0

        total_c5ai = sum(annual_by_type.values())
        total_c5ai = max(total_c5ai, 1.0)  # Guard against zero

        # Scale factor vs. static model
        if static_mean_annual_loss > 0:
            ratio = total_c5ai / static_mean_annual_loss
        else:
            ratio = 1.0

        # Loss breakdown fractions
        fractions: Dict[str, float] = {
            rt: round(loss / total_c5ai, 6) for rt, loss in annual_by_type.items()
        }
        # Normalise to sum exactly to 1.0
        frac_sum = sum(fractions.values())
        if frac_sum > 0:
            fractions = {k: v / frac_sum for k, v in fractions.items()}

        return OperatorAggregate(
            annual_expected_loss_by_type=annual_by_type,
            total_expected_annual_loss=total_c5ai,
            c5ai_vs_static_ratio=round(ratio, 6),
            loss_breakdown_fractions=fractions,
        )

    @staticmethod
    def _overall_quality(flags: List[str]) -> str:
        """Return the worst quality flag across all sites."""
        priority = ["PRIOR_ONLY", "POOR", "LIMITED", "SUFFICIENT"]
        for flag in priority:
            if flag in flags:
                return flag
        return "SUFFICIENT"

    @staticmethod
    def _confidence_label(flags: List[str]) -> str:
        worst = ForecastPipeline._overall_quality(flags)
        return {"SUFFICIENT": "high", "LIMITED": "medium", "POOR": "low", "PRIOR_ONLY": "low"}.get(
            worst, "low"
        )


# ── CLI entry point ───────────────────────────────────────────────────────────

def _cli():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="C5AI+ v5.0 – Biological Risk Forecaster")
    parser.add_argument("--input", "-i", required=True, help="Path to C5AI+ input JSON")
    parser.add_argument("--output", "-o", default="risk_forecast.json", help="Output forecast JSON")
    parser.add_argument("--static-loss", "-s", type=float, default=0.0,
                        help="Static model E[annual loss] in NOK (for ratio calculation)")
    args = parser.parse_args()

    from c5ai_plus.ingestion.data_loader import DataLoader
    loader = DataLoader()
    operator_input = loader.load_from_json(args.input)

    pipeline = ForecastPipeline(verbose=True)
    pipeline.run(
        operator_input,
        static_mean_annual_loss=args.static_loss,
        output_path=args.output,
    )


if __name__ == "__main__":
    _cli()

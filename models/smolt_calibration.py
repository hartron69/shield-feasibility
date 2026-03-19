"""
SmoltMCCalibrator

Calibrates MonteCarloEngine parameters for the smolt risk profile.
Output is fed directly into the existing MonteCarloEngine via SmoltOperatorBuilder.

Accounts for:
- Number of facilities and their RAS type
- Claims-free history (frequency discount)
- TIV composition (machinery-heavy → higher severity CV)
- BI dominance (high BI share → longer loss tail)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from data.input_schema import SmoltOperatorInput
from risk_domains.ras_systems import RAS_PERILS, RASRiskDomain


@dataclass
class SmoltMCParameters:
    """Calibrated Monte Carlo parameters for one smolt operator."""
    # Core model parameters (compatible with OperatorInput.risk_params)
    expected_annual_events:   float
    mean_loss_severity_nok:   float
    cv_loss_severity:         float
    catastrophe_probability:  float
    catastrophe_multiplier:   float
    inter_site_correlation:   float
    # Additional info for reporting
    dominant_peril:           str
    ras_expected_annual_loss: float
    history_discount_applied: float


class SmoltMCCalibrator:
    """
    Calibrates MC parameters from SmoltOperatorInput.

    Takes into account:
    - Number of facilities and RAS type
    - Claims-free history (frequency discount)
    - TIV composition (machinery-heavy → higher severity CV)
    - BI dominance (high BI share → longer loss tail)
    """

    def calibrate(self, smolt_input: SmoltOperatorInput) -> SmoltMCParameters:
        prop_tiv = sum(
            f.building_total_nok + f.machinery_nok
            for f in smolt_input.facilities
        )
        n   = smolt_input.n_facilities
        ras = RASRiskDomain(prop_tiv, smolt_input.claims_history_years)

        # BI dominance increases loss severity tail
        total_tiv = smolt_input.total_tiv_nok
        bi_share  = (
            sum(f.bi_sum_insured_nok for f in smolt_input.facilities) / total_tiv
            if total_tiv else 0.0
        )
        bi_severity_adder = bi_share * 0.40   # BI-heavy → up to 40% higher CV

        # Inter-site correlation decreases weakly with more facilities
        # (separate watersheds, but shared management practices)
        inter_corr = max(0.05, 0.15 - (n - 1) * 0.02)

        # Dominant peril: highest expected loss contribution
        dominant_peril = max(
            RAS_PERILS.items(),
            key=lambda kv: (kv[1].annual_frequency_base
                            * kv[1].severity_as_pct_of_property[0]),
        )[0]

        return SmoltMCParameters(
            expected_annual_events   = ras.aggregate_frequency * n,
            mean_loss_severity_nok   = (
                ras.expected_annual_loss_nok
                / max(ras.aggregate_frequency * n, 1e-9)
            ),
            cv_loss_severity         = 0.65 + bi_severity_adder,
            catastrophe_probability  = 0.03,
            catastrophe_multiplier   = 4.5,
            inter_site_correlation   = inter_corr,
            dominant_peril           = dominant_peril,
            ras_expected_annual_loss = ras.expected_annual_loss_nok,
            history_discount_applied = ras.discount,
        )

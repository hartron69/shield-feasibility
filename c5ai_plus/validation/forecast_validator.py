"""
C5AI+ v5.0 – Forecast Validator.

Validates the structure and content of a risk_forecast.json before it
is consumed by the PCC Feasibility Tool.

Validation rules
----------------
  1. Required top-level keys are present
  2. metadata.model_version is a non-empty string
  3. At least one site_forecast is present
  4. Each RiskTypeForecast has valid numeric ranges:
       – event_probability ∈ [0, 1]
       – expected_loss_mean ≥ 0
       – confidence_score ∈ [0, 1]
  5. operator_aggregate.c5ai_vs_static_ratio > 0
  6. operator_aggregate.loss_breakdown_fractions sum to ~1.0
"""

from __future__ import annotations

from typing import List, Tuple

from c5ai_plus.data_models.forecast_schema import RiskForecast, RISK_TYPES


class ValidationError(Exception):
    """Raised when a RiskForecast fails validation."""


class ForecastValidator:
    """
    Validate a RiskForecast object.

    Usage
    -----
    >>> validator = ForecastValidator()
    >>> errors = validator.validate(forecast)
    >>> if errors:
    ...     raise ValidationError(errors)
    """

    def validate(self, forecast: RiskForecast) -> List[str]:
        """
        Run all validation checks.

        Returns
        -------
        List[str]
            List of error messages. Empty list means valid.
        """
        errors: List[str] = []
        errors.extend(self._validate_metadata(forecast))
        errors.extend(self._validate_site_forecasts(forecast))
        errors.extend(self._validate_operator_aggregate(forecast))
        return errors

    def validate_or_raise(self, forecast: RiskForecast) -> None:
        """Validate and raise ValidationError if any errors are found."""
        errors = self.validate(forecast)
        if errors:
            msg = "C5AI+ forecast validation failed:\n" + "\n".join(
                f"  [{i+1}] {e}" for i, e in enumerate(errors)
            )
            raise ValidationError(msg)

    # ── Sub-validators ────────────────────────────────────────────────────────

    def _validate_metadata(self, forecast: RiskForecast) -> List[str]:
        errors = []
        meta = forecast.metadata
        if not meta.model_version:
            errors.append("metadata.model_version is empty.")
        if not meta.operator_id:
            errors.append("metadata.operator_id is empty.")
        if not meta.generated_at:
            errors.append("metadata.generated_at is empty.")
        if meta.forecast_horizon_years < 1:
            errors.append(
                f"metadata.forecast_horizon_years must be ≥ 1, got {meta.forecast_horizon_years}."
            )
        return errors

    def _validate_site_forecasts(self, forecast: RiskForecast) -> List[str]:
        errors = []
        if not forecast.site_forecasts:
            errors.append("site_forecasts is empty – at least one site is required.")
            return errors

        for sf in forecast.site_forecasts:
            prefix = f"site '{sf.site_id}'"
            if not sf.annual_forecasts:
                errors.append(f"{prefix}: annual_forecasts is empty.")
                continue
            for rtf in sf.annual_forecasts:
                p = f"{prefix} risk_type='{rtf.risk_type}' year={rtf.year}"
                if rtf.risk_type not in RISK_TYPES:
                    errors.append(f"{p}: unknown risk_type '{rtf.risk_type}'.")
                if not (0.0 <= rtf.event_probability <= 1.0):
                    errors.append(
                        f"{p}: event_probability={rtf.event_probability} out of [0, 1]."
                    )
                if rtf.expected_loss_mean < 0:
                    errors.append(
                        f"{p}: expected_loss_mean={rtf.expected_loss_mean} is negative."
                    )
                if not (0.0 <= rtf.confidence_score <= 1.0):
                    errors.append(
                        f"{p}: confidence_score={rtf.confidence_score} out of [0, 1]."
                    )
        return errors

    def _validate_operator_aggregate(self, forecast: RiskForecast) -> List[str]:
        errors = []
        agg = forecast.operator_aggregate

        if agg.total_expected_annual_loss < 0:
            errors.append(
                f"operator_aggregate.total_expected_annual_loss is negative: "
                f"{agg.total_expected_annual_loss}"
            )
        if agg.c5ai_vs_static_ratio <= 0:
            errors.append(
                f"operator_aggregate.c5ai_vs_static_ratio must be > 0, "
                f"got {agg.c5ai_vs_static_ratio}"
            )
        if agg.c5ai_vs_static_ratio > 5.0:
            errors.append(
                f"operator_aggregate.c5ai_vs_static_ratio={agg.c5ai_vs_static_ratio} "
                f"seems unreasonably high (> 5.0). Check inputs."
            )

        frac_sum = sum(agg.loss_breakdown_fractions.values())
        if agg.loss_breakdown_fractions and abs(frac_sum - 1.0) > 0.01:
            errors.append(
                f"operator_aggregate.loss_breakdown_fractions sum to {frac_sum:.4f}, "
                f"expected ~1.0."
            )

        return errors

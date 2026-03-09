"""
Tests for C5AI+ forecast validator.
"""

import pytest

from c5ai_plus.data_models.forecast_schema import (
    ForecastMetadata, OperatorAggregate, RiskForecast, RiskTypeForecast, SiteForecast,
)
from c5ai_plus.validation.forecast_validator import ForecastValidator, ValidationError


def _minimal_forecast(
    ratio=1.0,
    prob=0.12,
    loss=3_000_000,
    fractions=None,
) -> RiskForecast:
    if fractions is None:
        fractions = {"hab": 0.5, "lice": 0.3, "jellyfish": 0.1, "pathogen": 0.1}
    return RiskForecast(
        metadata=ForecastMetadata(
            model_version="5.0.0",
            generated_at="2026-03-06T10:00:00+00:00",
            operator_id="test-op",
            operator_name="Test Op",
            forecast_horizon_years=5,
            overall_confidence="medium",
            overall_data_quality="SUFFICIENT",
            sites_included=["s1"],
        ),
        site_forecasts=[
            SiteForecast(
                site_id="s1",
                site_name="Site One",
                annual_forecasts=[
                    RiskTypeForecast(
                        risk_type="hab", year=1,
                        event_probability=prob,
                        expected_loss_mean=loss,
                        expected_loss_p50=loss * 0.7,
                        expected_loss_p90=loss * 2.0,
                        confidence_score=0.8,
                        data_quality_flag="SUFFICIENT",
                    )
                ],
            )
        ],
        operator_aggregate=OperatorAggregate(
            annual_expected_loss_by_type={"hab": loss, "lice": 0, "jellyfish": 0, "pathogen": 0},
            total_expected_annual_loss=loss,
            c5ai_vs_static_ratio=ratio,
            loss_breakdown_fractions=fractions,
        ),
    )


class TestForecastValidator:
    def setup_method(self):
        self.v = ForecastValidator()

    def test_valid_forecast_no_errors(self):
        fc = _minimal_forecast()
        errors = self.v.validate(fc)
        assert errors == []

    def test_invalid_prob_out_of_range(self):
        fc = _minimal_forecast(prob=1.5)
        errors = self.v.validate(fc)
        assert any("event_probability" in e for e in errors)

    def test_invalid_negative_loss(self):
        fc = _minimal_forecast(loss=-100)
        errors = self.v.validate(fc)
        assert any("expected_loss_mean" in e for e in errors)

    def test_ratio_zero_fails(self):
        fc = _minimal_forecast(ratio=0.0)
        errors = self.v.validate(fc)
        assert any("c5ai_vs_static_ratio" in e for e in errors)

    def test_ratio_too_high_warns(self):
        fc = _minimal_forecast(ratio=6.0)
        errors = self.v.validate(fc)
        assert any("c5ai_vs_static_ratio" in e for e in errors)

    def test_fractions_not_sum_to_one_fails(self):
        fc = _minimal_forecast(fractions={"hab": 0.3, "lice": 0.2, "jellyfish": 0.1, "pathogen": 0.1})
        errors = self.v.validate(fc)
        assert any("loss_breakdown_fractions" in e for e in errors)

    def test_empty_site_forecasts(self):
        fc = _minimal_forecast()
        fc.site_forecasts[0].annual_forecasts = []
        errors = self.v.validate(fc)
        assert any("annual_forecasts" in e for e in errors)

    def test_validate_or_raise_clean(self):
        fc = _minimal_forecast()
        self.v.validate_or_raise(fc)  # Should not raise

    def test_validate_or_raise_raises_on_error(self):
        fc = _minimal_forecast(ratio=-1.0)
        with pytest.raises(ValidationError):
            self.v.validate_or_raise(fc)

    def test_unknown_risk_type_fails(self):
        fc = _minimal_forecast()
        fc.site_forecasts[0].annual_forecasts[0].risk_type = "volcano"
        errors = self.v.validate(fc)
        assert any("risk_type" in e for e in errors)

    def test_missing_metadata_version(self):
        fc = _minimal_forecast()
        fc.metadata.model_version = ""
        errors = self.v.validate(fc)
        assert any("model_version" in e for e in errors)

"""
Tests for C5AI+ forecast schema – serialisation, deserialisation, and accessors.
"""

import json
import pytest

from c5ai_plus.data_models.forecast_schema import (
    ForecastMetadata,
    OperatorAggregate,
    RiskForecast,
    RiskTypeForecast,
    SiteForecast,
    RISK_TYPES,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_rtf(risk_type="hab", year=1, prob=0.12, loss=3_000_000):
    return RiskTypeForecast(
        risk_type=risk_type,
        year=year,
        event_probability=prob,
        expected_loss_mean=loss,
        expected_loss_p50=loss * 0.7,
        expected_loss_p90=loss * 2.1,
        confidence_score=0.72,
        data_quality_flag="LIMITED",
        model_used="prior",
    )


def _make_forecast() -> RiskForecast:
    metadata = ForecastMetadata(
        model_version="5.0.0",
        generated_at="2026-03-06T10:00:00+00:00",
        operator_id="nordic-aqua-001",
        operator_name="Nordic Aqua Partners AS",
        forecast_horizon_years=5,
        overall_confidence="medium",
        overall_data_quality="LIMITED",
        sites_included=["site-001", "site-002"],
        warnings=["Limited env data for site-002"],
    )

    site1_forecasts = [
        _make_rtf("hab", yr, 0.12, 3_000_000) for yr in range(1, 6)
    ] + [
        _make_rtf("lice", yr, 0.28, 1_500_000) for yr in range(1, 6)
    ] + [
        _make_rtf("jellyfish", yr, 0.08, 500_000) for yr in range(1, 6)
    ] + [
        _make_rtf("pathogen", yr, 0.10, 800_000) for yr in range(1, 6)
    ]

    site1 = SiteForecast("site-001", "Hardanger Nord", site1_forecasts)
    site2 = SiteForecast("site-002", "Hardanger Sor", [
        _make_rtf(rt, yr, 0.10, 2_000_000)
        for rt in RISK_TYPES for yr in range(1, 6)
    ])

    aggregate = OperatorAggregate(
        annual_expected_loss_by_type={"hab": 4_500_000, "lice": 2_100_000,
                                       "jellyfish": 800_000, "pathogen": 1_200_000},
        total_expected_annual_loss=8_600_000,
        c5ai_vs_static_ratio=0.92,
        loss_breakdown_fractions={"hab": 0.523, "lice": 0.244,
                                   "jellyfish": 0.093, "pathogen": 0.140},
    )

    return RiskForecast(
        metadata=metadata,
        site_forecasts=[site1, site2],
        operator_aggregate=aggregate,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRiskTypeForecast:
    def test_fields_populated(self):
        rtf = _make_rtf()
        assert rtf.risk_type == "hab"
        assert rtf.year == 1
        assert 0 <= rtf.event_probability <= 1
        assert rtf.expected_loss_mean > 0
        assert rtf.confidence_score == 0.72

    def test_risk_type_is_valid(self):
        rtf = _make_rtf("lice")
        assert rtf.risk_type in RISK_TYPES


class TestSiteForecast:
    def test_get_forecast_found(self):
        sf = SiteForecast("s1", "Site One", [_make_rtf("hab", 2)])
        result = sf.get_forecast("hab", 2)
        assert result is not None
        assert result.year == 2

    def test_get_forecast_not_found(self):
        sf = SiteForecast("s1", "Site One", [_make_rtf("hab", 1)])
        assert sf.get_forecast("hab", 99) is None

    def test_total_expected_loss_nok(self):
        sf = SiteForecast("s1", "Site One", [
            _make_rtf("hab", 1, loss=1_000_000),
            _make_rtf("lice", 1, loss=2_000_000),
        ])
        assert sf.total_expected_loss_nok(year=1) == pytest.approx(3_000_000)

    def test_total_loss_wrong_year_zero(self):
        sf = SiteForecast("s1", "Site One", [_make_rtf("hab", 1, loss=1_000_000)])
        assert sf.total_expected_loss_nok(year=2) == 0.0


class TestRiskForecast:
    def test_scale_factor(self):
        fc = _make_forecast()
        assert fc.scale_factor == pytest.approx(0.92)

    def test_total_expected_annual_loss(self):
        fc = _make_forecast()
        assert fc.total_expected_annual_loss == pytest.approx(8_600_000)

    def test_loss_fractions_sum(self):
        fc = _make_forecast()
        total = sum(fc.loss_fractions.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_to_dict_roundtrip(self):
        fc = _make_forecast()
        d = fc.to_dict()
        fc2 = RiskForecast.from_dict(d)
        assert fc2.metadata.operator_id == fc.metadata.operator_id
        assert fc2.operator_aggregate.c5ai_vs_static_ratio == fc.operator_aggregate.c5ai_vs_static_ratio
        assert len(fc2.site_forecasts) == len(fc.site_forecasts)

    def test_to_json_and_back(self):
        fc = _make_forecast()
        json_str = fc.to_json()
        data = json.loads(json_str)
        fc2 = RiskForecast.from_dict(data)
        assert fc2.metadata.model_version == "5.0.0"
        assert fc2.site_forecasts[0].site_id == "site-001"

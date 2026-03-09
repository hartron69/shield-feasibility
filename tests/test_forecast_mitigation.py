"""
Tests for Sprint 2 Parts C & D – Forecast-Level Mitigation and MC Integration.

Verifies that apply_mitigations_to_forecast() adjusts the C5AI+ risk
forecast before Monte Carlo runs, and that MonteCarloEngine can operate
on a mitigated forecast with the correct provenance flags set.
"""

import json
import numpy as np
import pytest
from pathlib import Path

from analysis.mitigation import (
    MitigationAction,
    PREDEFINED_MITIGATIONS,
    apply_mitigations_to_forecast,
)
from c5ai_plus.data_models.forecast_schema import (
    RiskForecast,
    RiskTypeForecast,
    SiteForecast,
    OperatorAggregate,
    ForecastMetadata,
    RISK_TYPES,
)
from data.input_schema import validate_input
from models.monte_carlo import MonteCarloEngine, SimulationResults


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_forecast(scale=1.0, operator_id="op-001"):
    """Construct a minimal valid RiskForecast for testing."""
    meta = ForecastMetadata(
        model_version="5.0.0",
        generated_at="2026-03-06T10:00:00+00:00",
        operator_id=operator_id,
        operator_name="Test Aqua AS",
        forecast_horizon_years=5,
        overall_confidence="medium",
        overall_data_quality="LIMITED",
        sites_included=["site-001"],
        warnings=[],
    )
    annual_forecasts = [
        RiskTypeForecast(
            risk_type=rt,
            year=yr,
            event_probability=0.20,
            expected_loss_mean=2_000_000,
            expected_loss_p50=1_400_000,
            expected_loss_p90=4_200_000,
            confidence_score=0.65,
            data_quality_flag="LIMITED",
            model_used="prior",
        )
        for rt in RISK_TYPES
        for yr in range(1, 6)
    ]
    sf = SiteForecast(site_id="site-001", site_name="Test Site", annual_forecasts=annual_forecasts)
    agg = OperatorAggregate(
        annual_expected_loss_by_type={"hab": 4_000_000, "lice": 2_000_000,
                                       "jellyfish": 1_000_000, "pathogen": 1_000_000},
        total_expected_annual_loss=8_000_000,
        c5ai_vs_static_ratio=scale,
        loss_breakdown_fractions={"hab": 0.50, "lice": 0.25,
                                   "jellyfish": 0.125, "pathogen": 0.125},
    )
    return RiskForecast(metadata=meta, site_forecasts=[sf], operator_aggregate=agg)


SAMPLE_OPERATOR = {
    "name": "Test Aqua AS",
    "registration_number": "123456789",
    "country": "Norway",
    "reporting_currency": "NOK",
    "sites": [{
        "name": "Test Site",
        "location": "Hordaland",
        "species": "Atlantic Salmon",
        "biomass_tonnes": 1000,
        "biomass_value_per_tonne": 72000,
        "equipment_value": 20_000_000,
        "infrastructure_value": 10_000_000,
        "annual_revenue": 180_000_000,
    }],
    "current_insurance": {
        "annual_premium": 19_500_000,
        "per_occurrence_deductible": 500_000,
        "annual_aggregate_deductible": 1_000_000,
        "coverage_limit": 200_000_000,
        "aggregate_limit": 300_000_000,
        "coverage_lines": ["Mortality", "Property"],
        "insurer_names": ["Test Insurer AS"],
        "current_loss_ratio": 0.45,
        "market_rating_trend": 0.05,
    },
    "historical_losses": [],
    "financials": {
        "annual_revenue": 180_000_000,
        "ebitda": 36_000_000,
        "total_assets": 400_000_000,
        "net_equity": 200_000_000,
        "credit_rating": None,
        "free_cash_flow": 25_000_000,
        "years_in_operation": 8,
    },
    "risk_params": {
        "expected_annual_events": 3.2,
        "mean_loss_severity": 7_100_000,
        "cv_loss_severity": 1.2,
        "catastrophe_probability": 0.05,
        "catastrophe_loss_multiplier": 5.0,
        "inter_site_correlation": 0.3,
        "bi_trigger_threshold": 1_000_000,
        "bi_daily_revenue_loss": 50_000,
        "bi_average_interruption_days": 30,
    },
}


# ── Part C: apply_mitigations_to_forecast ────────────────────────────────────

class TestApplyMitigationsToForecast:
    def test_no_actions_returns_original(self):
        forecast = _make_forecast()
        result = apply_mitigations_to_forecast(forecast, [])
        assert result is forecast  # same object returned

    def test_returns_deep_copy_not_mutation(self):
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        result = apply_mitigations_to_forecast(forecast, [action])
        # Original forecast should be unchanged
        for sf in forecast.site_forecasts:
            for rtf in sf.annual_forecasts:
                assert rtf.baseline_event_probability is None

    def test_jellyfish_action_reduces_jellyfish_probability(self):
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        result = apply_mitigations_to_forecast(forecast, [action])
        for sf in result.site_forecasts:
            for rtf in sf.annual_forecasts:
                if rtf.risk_type == "jellyfish":
                    assert rtf.event_probability < 0.20  # was 0.20
                    assert rtf.baseline_event_probability == pytest.approx(0.20)

    def test_jellyfish_action_does_not_change_lice_probability(self):
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        result = apply_mitigations_to_forecast(forecast, [action])
        for sf in result.site_forecasts:
            for rtf in sf.annual_forecasts:
                if rtf.risk_type == "lice":
                    assert rtf.event_probability == pytest.approx(0.20)

    def test_jellyfish_action_does_not_change_hab_probability(self):
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        result = apply_mitigations_to_forecast(forecast, [action])
        for sf in result.site_forecasts:
            for rtf in sf.annual_forecasts:
                if rtf.risk_type == "hab":
                    assert rtf.event_probability == pytest.approx(0.20)

    def test_lice_action_reduces_lice_only(self):
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        result = apply_mitigations_to_forecast(forecast, [action])
        for sf in result.site_forecasts:
            for rtf in sf.annual_forecasts:
                if rtf.risk_type == "lice":
                    assert rtf.event_probability < 0.20
                elif rtf.risk_type in ("hab", "pathogen"):
                    assert rtf.event_probability == pytest.approx(0.20)

    def test_severity_reduction_applied_to_loss_mean(self):
        """Severity-focused actions reduce expected_loss_mean."""
        forecast = _make_forecast()
        action = MitigationAction(
            name="sev_only",
            description="severity only",
            applies_to_domains=[],
            severity_reduction=0.30,
            targeted_risk_types=["lice"],
            mitigation_mode="severity",
        )
        result = apply_mitigations_to_forecast(forecast, [action])
        for sf in result.site_forecasts:
            for rtf in sf.annual_forecasts:
                if rtf.risk_type == "lice":
                    assert rtf.expected_loss_mean == pytest.approx(2_000_000 * 0.70, rel=1e-6)
                    assert rtf.baseline_expected_loss_mean == pytest.approx(2_000_000)

    def test_probability_mode_does_not_change_loss_mean(self):
        """Probability-only mode should not change expected_loss_mean."""
        forecast = _make_forecast()
        action = MitigationAction(
            name="prob_only",
            description="prob only",
            applies_to_domains=[],
            probability_reduction=0.30,
            targeted_risk_types=["jellyfish"],
            mitigation_mode="probability",
        )
        result = apply_mitigations_to_forecast(forecast, [action])
        for sf in result.site_forecasts:
            for rtf in sf.annual_forecasts:
                if rtf.risk_type == "jellyfish":
                    assert rtf.expected_loss_mean == pytest.approx(2_000_000)
                    assert rtf.event_probability < 0.20

    def test_applied_mitigations_recorded_in_rtf(self):
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        result = apply_mitigations_to_forecast(forecast, [action])
        for sf in result.site_forecasts:
            for rtf in sf.annual_forecasts:
                if rtf.risk_type == "jellyfish":
                    assert "jellyfish_mitigation" in rtf.applied_mitigations

    def test_applied_mitigations_in_metadata(self):
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        result = apply_mitigations_to_forecast(forecast, [action])
        assert "lice_barriers" in result.metadata.applied_mitigations

    def test_operator_aggregate_recomputed(self):
        """total_expected_annual_loss must decrease after mitigation."""
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        result = apply_mitigations_to_forecast(forecast, [action])
        assert result.operator_aggregate.total_expected_annual_loss < 8_000_000

    def test_baseline_total_preserved(self):
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        result = apply_mitigations_to_forecast(forecast, [action])
        assert result.operator_aggregate.baseline_total_expected_annual_loss == pytest.approx(8_000_000)

    def test_scale_ratio_reduced_after_mitigation(self):
        forecast = _make_forecast(scale=1.20)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        result = apply_mitigations_to_forecast(forecast, [action])
        assert result.operator_aggregate.c5ai_vs_static_ratio < 1.20

    def test_loss_fractions_still_sum_to_one(self):
        forecast = _make_forecast()
        actions = [
            PREDEFINED_MITIGATIONS["jellyfish_mitigation"],
            PREDEFINED_MITIGATIONS["lice_barriers"],
        ]
        result = apply_mitigations_to_forecast(forecast, actions)
        frac_sum = sum(result.operator_aggregate.loss_breakdown_fractions.values())
        assert abs(frac_sum - 1.0) < 1e-6

    def test_portfolio_wide_action_reduces_all_risk_types(self):
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["risk_manager_hire"]
        result = apply_mitigations_to_forecast(forecast, [action])
        for sf in result.site_forecasts:
            for rtf in sf.annual_forecasts:
                # Severity reduction applied to all
                assert rtf.expected_loss_mean < 2_000_000

    def test_probability_non_negative_after_mitigation(self):
        """Aggressive reductions should not produce negative probabilities."""
        forecast = _make_forecast()
        action = MitigationAction(
            name="extreme", description="",
            applies_to_domains=[],
            probability_reduction=0.99,
            targeted_risk_types=["jellyfish"],
            mitigation_mode="probability",
        )
        result = apply_mitigations_to_forecast(forecast, [action])
        for sf in result.site_forecasts:
            for rtf in sf.annual_forecasts:
                assert rtf.event_probability >= 0.0


# ── Uncertainty in forecast mitigation ────────────────────────────────────────

class TestForecastMitigationUncertainty:
    def test_uncertainty_mode_produces_different_result(self):
        """Two stochastic draws should generally differ."""
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]

        result1 = apply_mitigations_to_forecast(
            forecast, [action], use_uncertainty=True, rng=np.random.default_rng(1)
        )
        result2 = apply_mitigations_to_forecast(
            forecast, [action], use_uncertainty=True, rng=np.random.default_rng(2)
        )
        # With different RNG seeds the results should differ
        probs1 = [
            rtf.event_probability
            for sf in result1.site_forecasts
            for rtf in sf.annual_forecasts
            if rtf.risk_type == "jellyfish"
        ]
        probs2 = [
            rtf.event_probability
            for sf in result2.site_forecasts
            for rtf in sf.annual_forecasts
            if rtf.risk_type == "jellyfish"
        ]
        assert probs1 != probs2

    def test_uncertainty_still_reduces_from_baseline(self):
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        result = apply_mitigations_to_forecast(
            forecast, [action], use_uncertainty=True, rng=np.random.default_rng(42)
        )
        for sf in result.site_forecasts:
            for rtf in sf.annual_forecasts:
                if rtf.risk_type == "jellyfish":
                    # Even stochastic draw should reduce probability
                    assert rtf.event_probability < 0.20


# ── Part D: Monte Carlo integration with pre-loaded forecast ──────────────────

class TestMCIntegrationWithMitigatedForecast:
    def _make_engine(self, forecast=None, n=500):
        operator = validate_input(SAMPLE_OPERATOR)
        return MonteCarloEngine(
            operator, n_simulations=n, seed=42,
            pre_loaded_forecast=forecast,
        )

    def test_no_preloaded_forecast_works_as_before(self):
        """Without pre-loaded forecast, engine behaves identically to original."""
        engine = self._make_engine(forecast=None, n=300)
        result = engine.run()
        assert result.mitigated is False
        assert result.mitigation_summary is None
        assert result.c5ai_enriched is False

    def test_preloaded_forecast_applied(self):
        forecast = _make_forecast(scale=1.20)
        engine = self._make_engine(forecast=forecast, n=300)
        result = engine.run()
        assert result.c5ai_enriched is True
        assert result.c5ai_scale_factor == pytest.approx(1.20)

    def test_mitigated_flag_false_for_unmitigated_forecast(self):
        """Pre-loaded forecast without applied_mitigations → mitigated=False."""
        forecast = _make_forecast(scale=1.0)
        engine = self._make_engine(forecast=forecast, n=200)
        result = engine.run()
        assert result.mitigated is False

    def test_mitigated_flag_true_after_apply_mitigations(self):
        """After apply_mitigations_to_forecast, the engine should set mitigated=True."""
        forecast = _make_forecast(scale=1.0)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        adjusted = apply_mitigations_to_forecast(forecast, [action])

        engine = self._make_engine(forecast=adjusted, n=200)
        result = engine.run()
        assert result.mitigated is True

    def test_mitigation_summary_populated(self):
        forecast = _make_forecast(scale=1.0)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        adjusted = apply_mitigations_to_forecast(forecast, [action])

        engine = self._make_engine(forecast=adjusted, n=200)
        result = engine.run()
        assert result.mitigation_summary is not None
        assert "lice_barriers" in result.mitigation_summary

    def test_mitigated_forecast_lower_expected_loss(self):
        """
        Running MC on a mitigated forecast (lower scale ratio) should produce
        a lower expected annual loss than the baseline forecast.
        """
        baseline_forecast = _make_forecast(scale=1.0)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        mitigated_forecast = apply_mitigations_to_forecast(baseline_forecast, [action])

        baseline_engine = MonteCarloEngine(
            validate_input(SAMPLE_OPERATOR), n_simulations=2000, seed=42,
            pre_loaded_forecast=baseline_forecast,
        )
        mitigated_engine = MonteCarloEngine(
            validate_input(SAMPLE_OPERATOR), n_simulations=2000, seed=42,
            pre_loaded_forecast=mitigated_forecast,
        )

        baseline_result = baseline_engine.run()
        mitigated_result = mitigated_engine.run()

        assert mitigated_result.mean_annual_loss < baseline_result.mean_annual_loss

    def test_pre_loaded_takes_priority_over_file_path(self, tmp_path):
        """When pre_loaded_forecast is given, c5ai_forecast_path is ignored."""
        # Create a forecast file with a very different scale
        file_forecast = _make_forecast(scale=5.0)
        path = tmp_path / "forecast.json"
        path.write_text(file_forecast.to_json(), encoding="utf-8")

        # Pre-loaded forecast has scale=1.0
        pre_loaded = _make_forecast(scale=1.0)
        operator = validate_input({
            **SAMPLE_OPERATOR,
            "c5ai_forecast_path": str(path),
        })
        engine = MonteCarloEngine(
            operator, n_simulations=300, seed=42,
            pre_loaded_forecast=pre_loaded,
        )
        result = engine.run()
        # Should use pre_loaded (scale=1.0) not file (scale=5.0)
        assert result.c5ai_scale_factor == pytest.approx(1.0)

    def test_new_simulation_results_fields_default(self):
        """New fields have correct defaults in static (no-forecast) run."""
        engine = self._make_engine(forecast=None, n=200)
        result = engine.run()
        assert result.mitigated is False
        assert result.mitigation_summary is None

    def test_baseline_and_mitigated_var_comparison(self):
        """Mitigated SCR (VaR99.5) should be lower or equal to baseline."""
        baseline_forecast = _make_forecast(scale=1.0)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        mitigated_forecast = apply_mitigations_to_forecast(baseline_forecast, [action])

        baseline_result = MonteCarloEngine(
            validate_input(SAMPLE_OPERATOR), n_simulations=2000, seed=42,
            pre_loaded_forecast=baseline_forecast,
        ).run()

        mitigated_result = MonteCarloEngine(
            validate_input(SAMPLE_OPERATOR), n_simulations=2000, seed=42,
            pre_loaded_forecast=mitigated_forecast,
        ).run()

        assert mitigated_result.var_995 <= baseline_result.var_995


# ── Forecast schema round-trip with new fields ───────────────────────────────

class TestForecastSchemaRoundTrip:
    def test_to_dict_includes_applied_mitigations(self):
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        adjusted = apply_mitigations_to_forecast(forecast, [action])
        d = adjusted.to_dict()
        assert "applied_mitigations" in d["metadata"]
        assert "jellyfish_mitigation" in d["metadata"]["applied_mitigations"]

    def test_from_dict_roundtrip_preserves_baseline_fields(self):
        """Serialize and reload adjusted forecast; baseline fields survive."""
        forecast = _make_forecast()
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        adjusted = apply_mitigations_to_forecast(forecast, [action])

        d = adjusted.to_dict()
        reloaded = RiskForecast.from_dict(d)

        for sf in reloaded.site_forecasts:
            for rtf in sf.annual_forecasts:
                if rtf.risk_type == "jellyfish":
                    assert rtf.baseline_event_probability == pytest.approx(0.20)

    def test_from_dict_old_format_still_works(self):
        """Old JSON (no new fields) must still deserialise without error."""
        old_json_dict = {
            "metadata": {
                "model_version": "5.0.0",
                "generated_at": "2026-01-01T00:00:00+00:00",
                "operator_id": "op-old",
                "operator_name": "Old Aqua",
                "forecast_horizon_years": 5,
                "overall_confidence": "medium",
                "overall_data_quality": "LIMITED",
                "sites_included": ["s1"],
                "warnings": [],
                # No applied_mitigations key
            },
            "site_forecasts": [{
                "site_id": "s1",
                "site_name": "Site 1",
                "annual_forecasts": [{
                    "risk_type": "lice",
                    "year": 1,
                    "event_probability": 0.15,
                    "expected_loss_mean": 1_000_000,
                    "expected_loss_p50": 700_000,
                    "expected_loss_p90": 2_000_000,
                    "confidence_score": 0.7,
                    "data_quality_flag": "LIMITED",
                    "model_used": "prior",
                    # No baseline_ fields
                }],
            }],
            "operator_aggregate": {
                "annual_expected_loss_by_type": {"lice": 1_000_000},
                "total_expected_annual_loss": 1_000_000,
                "c5ai_vs_static_ratio": 1.0,
                "loss_breakdown_fractions": {"lice": 1.0},
                # No baseline_total_expected_annual_loss
            },
        }
        forecast = RiskForecast.from_dict(old_json_dict)
        assert forecast.metadata.applied_mitigations == []
        for sf in forecast.site_forecasts:
            for rtf in sf.annual_forecasts:
                assert rtf.baseline_event_probability is None
                assert rtf.applied_mitigations == []
        assert forecast.operator_aggregate.baseline_total_expected_annual_loss is None

"""
Tests for MonteCarloEngine with and without C5AI+ forecast integration.
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from data.input_schema import validate_input
from models.monte_carlo import MonteCarloEngine, SimulationResults


# ── Minimal operator fixture ──────────────────────────────────────────────────

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


def _make_engine(extra: dict = None, n: int = 500) -> MonteCarloEngine:
    raw = {**SAMPLE_OPERATOR, **(extra or {})}
    operator = validate_input(raw)
    return MonteCarloEngine(operator, n_simulations=n, seed=42)


# ── Static model tests ────────────────────────────────────────────────────────

class TestMonteCarloStatic:
    def test_run_returns_simulation_results(self):
        engine = _make_engine()
        result = engine.run()
        assert isinstance(result, SimulationResults)

    def test_annual_losses_shape(self):
        engine = _make_engine(n=100)
        result = engine.run()
        assert result.annual_losses.shape == (100, 5)

    def test_statistics_are_positive(self):
        result = _make_engine().run()
        assert result.mean_annual_loss > 0
        assert result.std_annual_loss > 0
        assert result.var_95 >= result.var_90
        assert result.var_995 >= result.var_99

    def test_tvar_geq_var95(self):
        result = _make_engine().run()
        assert result.tvar_95 >= result.var_95

    def test_5yr_stats_consistent(self):
        result = _make_engine().run()
        # mean 5yr ≈ 5 × mean annual (not exact due to CAT overlay)
        ratio = result.mean_5yr_loss / result.mean_annual_loss
        assert 4.0 <= ratio <= 6.0

    def test_c5ai_not_enriched_by_default(self):
        result = _make_engine().run()
        assert result.c5ai_enriched is False
        assert result.c5ai_scale_factor is None
        assert result.bio_loss_breakdown is None


# ── Fallback tests (invalid C5AI+ path) ───────────────────────────────────────

class TestMonteCarloFallback:
    def test_missing_c5ai_file_falls_back(self, tmp_path):
        """When c5ai_forecast_path points to a non-existent file, use static model."""
        import warnings
        engine = _make_engine(
            extra={"c5ai_forecast_path": str(tmp_path / "nonexistent.json")}
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = engine.run()

        assert result.c5ai_enriched is False
        assert result.c5ai_scale_factor is None
        assert any("not found" in str(w.message).lower() or "fallback" in str(w.message).lower()
                   for w in caught)

    def test_malformed_c5ai_file_falls_back(self, tmp_path):
        """Malformed JSON in forecast file triggers fallback."""
        import warnings
        forecast_path = tmp_path / "bad_forecast.json"
        forecast_path.write_text("NOT VALID JSON {{{")

        engine = _make_engine(extra={"c5ai_forecast_path": str(forecast_path)})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = engine.run()

        assert result.c5ai_enriched is False


# ── C5AI+ enrichment tests ────────────────────────────────────────────────────

class TestMonteCarloC5AIEnrichment:
    def _write_forecast(self, tmp_path, scale: float = 1.20) -> str:
        """Write a minimal but valid risk_forecast.json for testing."""
        forecast = {
            "metadata": {
                "model_version": "5.0.0",
                "generated_at": "2026-03-06T10:00:00+00:00",
                "operator_id": "test-op",
                "operator_name": "Test Aqua AS",
                "forecast_horizon_years": 5,
                "overall_confidence": "medium",
                "overall_data_quality": "LIMITED",
                "sites_included": ["site-001"],
                "warnings": [],
            },
            "site_forecasts": [{
                "site_id": "site-001",
                "site_name": "Test Site",
                "annual_forecasts": [
                    {
                        "risk_type": rt,
                        "year": yr,
                        "event_probability": 0.15,
                        "expected_loss_mean": 2_000_000,
                        "expected_loss_p50": 1_400_000,
                        "expected_loss_p90": 4_200_000,
                        "confidence_score": 0.65,
                        "data_quality_flag": "LIMITED",
                        "model_used": "prior",
                    }
                    for rt in ["hab", "lice", "jellyfish", "pathogen"]
                    for yr in range(1, 6)
                ],
            }],
            "operator_aggregate": {
                "annual_expected_loss_by_type": {
                    "hab": 4_000_000, "lice": 2_000_000,
                    "jellyfish": 1_000_000, "pathogen": 1_000_000,
                },
                "total_expected_annual_loss": 8_000_000,
                "c5ai_vs_static_ratio": scale,
                "loss_breakdown_fractions": {
                    "hab": 0.50, "lice": 0.25, "jellyfish": 0.125, "pathogen": 0.125,
                },
            },
        }
        path = tmp_path / "risk_forecast.json"
        path.write_text(json.dumps(forecast), encoding="utf-8")
        return str(path)

    def test_c5ai_enrichment_applied(self, tmp_path):
        path = self._write_forecast(tmp_path, scale=1.20)
        engine = _make_engine(extra={"c5ai_forecast_path": path})
        result = engine.run()
        assert result.c5ai_enriched is True
        assert result.c5ai_scale_factor == pytest.approx(1.20)

    def test_bio_breakdown_populated(self, tmp_path):
        path = self._write_forecast(tmp_path, scale=1.0)
        engine = _make_engine(extra={"c5ai_forecast_path": path}, n=200)
        result = engine.run()
        assert result.bio_loss_breakdown is not None
        assert "hab" in result.bio_loss_breakdown
        assert "lice" in result.bio_loss_breakdown
        assert result.bio_loss_breakdown["hab"].shape == (200, 5)

    def test_bio_breakdown_fractions_consistent(self, tmp_path):
        """Sum of bio breakdown fractions should equal total losses."""
        path = self._write_forecast(tmp_path, scale=1.0)
        engine = _make_engine(extra={"c5ai_forecast_path": path}, n=200)
        result = engine.run()
        bd = result.bio_loss_breakdown
        total_from_bd = sum(bd[rt] for rt in bd)
        np.testing.assert_allclose(
            total_from_bd, result.annual_losses, rtol=1e-6
        )

    def test_scale_above_one_increases_losses(self, tmp_path):
        """Scale factor > 1 should increase mean annual loss vs. static."""
        # Static run
        static_engine = _make_engine(n=2000)
        static_result = static_engine.run()

        # C5AI+ enriched run with scale=1.5
        path = self._write_forecast(tmp_path, scale=1.5)
        c5ai_engine = _make_engine(
            extra={"c5ai_forecast_path": path}, n=2000
        )
        c5ai_result = c5ai_engine.run()

        assert c5ai_result.mean_annual_loss == pytest.approx(
            static_result.mean_annual_loss * 1.5, rel=0.05
        )


# ── Sprint 1: backward compatibility + regime + correlation ───────────────────

class TestSprintOneBackwardCompatibility:
    """
    Existing behaviour must be unchanged when no regime_model / correlation
    is passed (the default).
    """

    def test_new_fields_populated_by_default(self):
        """portfolio_loss_distribution and site_loss_distribution are always set."""
        result = _make_engine(n=200).run()
        # portfolio_loss_distribution is always computed
        assert result.portfolio_loss_distribution is not None
        assert result.portfolio_loss_distribution.shape == (200,)

    def test_portfolio_loss_is_5yr_sum(self):
        """portfolio_loss_distribution must equal annual_losses.sum(axis=1)."""
        result = _make_engine(n=300).run()
        expected = result.annual_losses.sum(axis=1)
        np.testing.assert_allclose(
            result.portfolio_loss_distribution, expected, rtol=1e-10
        )

    def test_site_loss_distribution_populated(self):
        """Single-site operator → site_loss_distribution has one key."""
        result = _make_engine(n=100).run()
        assert result.site_loss_distribution is not None
        assert len(result.site_loss_distribution) == 1
        site_name = list(result.site_loss_distribution.keys())[0]
        assert result.site_loss_distribution[site_name].shape == (100, 5)

    def test_single_site_loss_equals_portfolio(self):
        """For a single-site operator, site loss == portfolio loss."""
        result = _make_engine(n=200).run()
        site_name = list(result.site_loss_distribution.keys())[0]
        np.testing.assert_allclose(
            result.site_loss_distribution[site_name],
            result.annual_losses,
            rtol=1e-10,
        )

    def test_cluster_year_indicator_none_by_default(self):
        result = _make_engine(n=100).run()
        assert result.cluster_year_indicator is None

    def test_aggregate_exhaustion_events_none(self):
        result = _make_engine(n=100).run()
        assert result.aggregate_exhaustion_events is None

    def test_existing_statistics_unchanged(self):
        """Sanity-check that core statistics still work after the changes."""
        result = _make_engine(n=500).run()
        assert result.mean_annual_loss > 0
        assert result.var_995 >= result.var_95
        assert result.tvar_95 >= result.var_95
        assert result.annual_losses.shape == (500, 5)


class TestSprintOneRegimeModel:
    """MonteCarloEngine with a RegimeModel."""

    def _engine_with_regime(self, n=500):
        from models.regime_model import RegimeModel
        operator = validate_input(SAMPLE_OPERATOR)
        rm = RegimeModel()  # uses PREDEFINED_REGIMES
        return MonteCarloEngine(operator, n_simulations=n, seed=42, regime_model=rm)

    def test_cluster_year_indicator_populated(self):
        engine = self._engine_with_regime()
        result = engine.run()
        assert result.cluster_year_indicator is not None
        assert result.cluster_year_indicator.shape == (500, 5)

    def test_cluster_year_indicator_values(self):
        """All indicator values must be valid regime multipliers."""
        from models.regime_model import PREDEFINED_REGIMES
        engine = self._engine_with_regime(n=200)
        result = engine.run()
        valid = {r.risk_multiplier for r in PREDEFINED_REGIMES.values()}
        unique = set(np.unique(result.cluster_year_indicator).tolist())
        assert unique.issubset(valid)

    def test_regime_increases_expected_loss(self):
        """Regime model (all multipliers ≥ 1) must increase or maintain mean loss."""
        from models.regime_model import RegimeModel
        static_result = _make_engine(n=3000).run()

        operator = validate_input(SAMPLE_OPERATOR)
        rm = RegimeModel()
        regime_engine = MonteCarloEngine(operator, n_simulations=3000, seed=42, regime_model=rm)
        regime_result = regime_engine.run()

        # With PREDEFINED_REGIMES all multipliers ≥ 1.0, so mean should be ≥ static
        assert regime_result.mean_annual_loss >= static_result.mean_annual_loss * 0.95

    def test_portfolio_loss_populated_with_regime(self):
        engine = self._engine_with_regime(n=200)
        result = engine.run()
        assert result.portfolio_loss_distribution is not None
        assert result.portfolio_loss_distribution.shape == (200,)

    def test_existing_stats_valid_with_regime(self):
        engine = self._engine_with_regime(n=500)
        result = engine.run()
        assert result.mean_annual_loss > 0
        assert result.var_995 >= result.var_95
        assert result.annual_losses.shape == (500, 5)

    def test_custom_two_regime_model(self):
        """from_dict creates a usable regime model."""
        from models.regime_model import RegimeModel
        d = {
            "normal": {"probability": 0.8, "risk_multiplier": 1.0},
            "stressed": {"probability": 0.2, "risk_multiplier": 4.0},
        }
        operator = validate_input(SAMPLE_OPERATOR)
        rm = RegimeModel.from_dict(d)
        engine = MonteCarloEngine(operator, n_simulations=200, seed=99, regime_model=rm)
        result = engine.run()
        assert result.cluster_year_indicator is not None
        valid_mults = {1.0, 4.0}
        unique = set(np.unique(result.cluster_year_indicator).tolist())
        assert unique.issubset(valid_mults)


class TestSprintOneCorrelation:
    """MonteCarloEngine with a RiskCorrelationMatrix (multi-site operator)."""

    MULTI_SITE_OPERATOR = {
        **SAMPLE_OPERATOR,
        "sites": [
            {
                "name": "Site Alpha",
                "location": "Hordaland",
                "species": "Atlantic Salmon",
                "biomass_tonnes": 800,
                "biomass_value_per_tonne": 72_000,
                "equipment_value": 15_000_000,
                "infrastructure_value": 8_000_000,
                "annual_revenue": 150_000_000,
            },
            {
                "name": "Site Beta",
                "location": "Rogaland",
                "species": "Atlantic Salmon",
                "biomass_tonnes": 600,
                "biomass_value_per_tonne": 72_000,
                "equipment_value": 12_000_000,
                "infrastructure_value": 6_000_000,
                "annual_revenue": 100_000_000,
            },
        ],
    }

    def _engine_with_correlation(self, rho=0.4, n=300):
        from models.correlation import RiskCorrelationMatrix
        operator = validate_input(self.MULTI_SITE_OPERATOR)
        corr = RiskCorrelationMatrix.equicorrelation(
            site_ids=["Site Alpha", "Site Beta"], rho=rho
        )
        return MonteCarloEngine(operator, n_simulations=n, seed=42, correlation=corr)

    def test_site_loss_distribution_has_two_keys(self):
        engine = self._engine_with_correlation()
        result = engine.run()
        assert result.site_loss_distribution is not None
        assert set(result.site_loss_distribution.keys()) == {"Site Alpha", "Site Beta"}

    def test_site_losses_shape(self):
        engine = self._engine_with_correlation(n=200)
        result = engine.run()
        for name, arr in result.site_loss_distribution.items():
            assert arr.shape == (200, 5), f"Bad shape for {name}"

    def test_site_losses_sum_to_portfolio(self):
        """Sum of site losses must equal portfolio losses for all (N, T) cells."""
        engine = self._engine_with_correlation(n=300)
        result = engine.run()
        sld = result.site_loss_distribution
        total_sites = sum(sld.values())
        np.testing.assert_allclose(
            total_sites, result.annual_losses, rtol=1e-8
        )

    def test_site_losses_non_negative(self):
        engine = self._engine_with_correlation(n=200)
        result = engine.run()
        for name, arr in result.site_loss_distribution.items():
            assert np.all(arr >= 0), f"Negative losses found for {name}"

    def test_cluster_year_none_without_regime(self):
        """Correlation alone does not set cluster_year_indicator."""
        engine = self._engine_with_correlation()
        result = engine.run()
        assert result.cluster_year_indicator is None

    def test_no_correlation_proportional_allocation(self):
        """Without correlation, site loss is strictly proportional to TIV."""
        operator = validate_input(self.MULTI_SITE_OPERATOR)
        engine = MonteCarloEngine(operator, n_simulations=200, seed=42)
        result = engine.run()
        sld = result.site_loss_distribution

        # Compute expected TIV weights
        sites = operator.sites
        tiv = np.array([s.total_insured_value for s in sites])
        w = tiv / tiv.sum()

        site_a = sld["Site Alpha"]
        expected_a = result.annual_losses * w[0]
        np.testing.assert_allclose(site_a, expected_a, rtol=1e-10)

    def test_combined_regime_and_correlation(self):
        """Engine accepts both regime_model and correlation simultaneously."""
        from models.regime_model import RegimeModel
        from models.correlation import RiskCorrelationMatrix
        operator = validate_input(self.MULTI_SITE_OPERATOR)
        rm = RegimeModel()
        corr = RiskCorrelationMatrix.equicorrelation(
            ["Site Alpha", "Site Beta"], rho=0.3
        )
        engine = MonteCarloEngine(
            operator, n_simulations=300, seed=0,
            regime_model=rm, correlation=corr
        )
        result = engine.run()
        assert result.cluster_year_indicator is not None
        assert result.site_loss_distribution is not None
        # Site losses sum to portfolio
        total = sum(result.site_loss_distribution.values())
        np.testing.assert_allclose(total, result.annual_losses, rtol=1e-8)

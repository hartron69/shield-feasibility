"""
Tests for Sprint 7 – MonteCarloEngine with domain_correlation parameter.

Covers backward compatibility (no correlation → None), forward path (correlation
provided → DomainLossBreakdown populated), reproducibility, total preservation,
and the C5AI+-enriched bio_modelled=True path via a mock forecast.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from data.input_schema import validate_input
from models.domain_correlation import DomainCorrelationMatrix, PREDEFINED_DOMAIN_CORRELATIONS
from models.domain_loss_breakdown import DOMAIN_SUBTYPES
from models.monte_carlo import MonteCarloEngine


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_SAMPLE_PATH = Path(__file__).parent.parent / "data" / "sample_input.json"


def _operator():
    with open(_SAMPLE_PATH) as f:
        raw = json.load(f)
    return validate_input(raw)


def _engine(domain_correlation=None, seed=42, n=500):
    return MonteCarloEngine(
        _operator(),
        n_simulations=n,
        seed=seed,
        domain_correlation=domain_correlation,
    )


def _expert():
    return DomainCorrelationMatrix.expert_default()


# ─────────────────────────────────────────────────────────────────────────────
# TestMCWithDomainCorrelation  (7 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestMCWithDomainCorrelation:
    def test_no_domain_correlation_gives_none_breakdown(self):
        engine = _engine(domain_correlation=None)
        results = engine.run()
        assert results.domain_loss_breakdown is None

    def test_with_domain_correlation_gives_breakdown(self):
        engine = _engine(domain_correlation=_expert())
        results = engine.run()
        assert results.domain_loss_breakdown is not None

    def test_domain_correlation_applied_flag_true(self):
        engine = _engine(domain_correlation=_expert())
        results = engine.run()
        assert results.domain_loss_breakdown.domain_correlation_applied is True

    def test_two_runs_same_seed_identical_breakdown(self):
        dbd1 = _engine(domain_correlation=_expert(), seed=7).run().domain_loss_breakdown
        dbd2 = _engine(domain_correlation=_expert(), seed=7).run().domain_loss_breakdown
        for st in dbd1.all_subtypes():
            np.testing.assert_array_equal(
                dbd1.all_subtypes()[st],
                dbd2.all_subtypes()[st],
                err_msg=f"Sub-type {st} differs between identical-seed runs.",
            )

    def test_total_preserved(self):
        engine = _engine(domain_correlation=_expert())
        results = engine.run()
        dbd = results.domain_loss_breakdown
        np.testing.assert_allclose(dbd.total(), results.annual_losses, rtol=1e-10)

    def test_expert_default_completes_without_error(self):
        engine = _engine(domain_correlation=PREDEFINED_DOMAIN_CORRELATIONS["expert_default"])
        results = engine.run()
        assert results is not None

    def test_all_16_subtype_keys_present(self):
        engine = _engine(domain_correlation=_expert())
        results = engine.run()
        dbd = results.domain_loss_breakdown
        expected_keys = set()
        for subtypes in DOMAIN_SUBTYPES.values():
            expected_keys.update(subtypes)
        actual_keys = set(dbd.all_subtypes().keys())
        assert actual_keys == expected_keys


# ─────────────────────────────────────────────────────────────────────────────
# TestMCDomainCorrelationWithC5AI  (3 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestMCDomainCorrelationWithC5AI:
    """
    Test the bio_modelled=True path by injecting a mock pre-loaded forecast.
    """

    def _mock_forecast(self):
        """Build a minimal mock RiskForecast that passes the validator."""
        fractions = {"hab": 0.40, "lice": 0.30, "jellyfish": 0.20, "pathogen": 0.10}
        scale = 1.05

        # Mock operator aggregate
        operator_agg = MagicMock()
        operator_agg.c5ai_vs_static_ratio = scale
        operator_agg.loss_breakdown_fractions = fractions

        # Mock metadata
        metadata = MagicMock()
        metadata.applied_mitigations = []

        # Mock forecast object — mimics what ForecastValidator.validate_or_raise inspects
        forecast = MagicMock()
        forecast.scale_factor = scale
        forecast.loss_fractions = fractions
        forecast.metadata = metadata
        forecast.operator_aggregate = operator_agg
        return forecast

    def _engine_with_forecast(self, forecast, domain_correlation=None, seed=42, n=300):
        return MonteCarloEngine(
            _operator(),
            n_simulations=n,
            seed=seed,
            domain_correlation=domain_correlation,
            pre_loaded_forecast=forecast,
        )

    def test_bio_modelled_true_with_correlation_total_preserved(self):
        # Build a realistic mock where bio_breakdown is proportional to annual_losses
        # (matching the real _apply_c5ai_forecast_obj behaviour).
        base_losses = np.random.default_rng(0).exponential(1e7, (300, 5))
        fracs = {"hab": 0.40, "lice": 0.30, "jellyfish": 0.20, "pathogen": 0.10}
        bio_bd = {rt: base_losses * f for rt, f in fracs.items()}

        forecast = self._mock_forecast()
        with patch(
            "models.monte_carlo.MonteCarloEngine._apply_c5ai_forecast_obj",
            return_value=(base_losses, 1.05, bio_bd, True),
        ):
            engine = self._engine_with_forecast(forecast, domain_correlation=_expert())
            results = engine.run()

        assert results.domain_loss_breakdown is not None
        np.testing.assert_allclose(
            results.domain_loss_breakdown.total(),
            results.annual_losses,
            rtol=1e-10,
        )

    def test_bio_slices_unchanged_from_c5ai(self):
        """When bio_modelled=True, bio sub-type arrays should match the C5AI+ output."""
        rng0 = np.random.default_rng(99)
        losses = rng0.exponential(1e7, (200, 5))
        fracs = {"hab": 0.40, "lice": 0.30, "jellyfish": 0.20, "pathogen": 0.10}
        bio_bd = {rt: losses * f for rt, f in fracs.items()}

        from models.domain_loss_breakdown import build_domain_loss_breakdown
        dbd = build_domain_loss_breakdown(
            losses,
            bio_breakdown=bio_bd,
            domain_correlation=_expert(),
            rng=np.random.default_rng(7),
        )
        assert dbd.bio_modelled is True
        for rt, arr in bio_bd.items():
            np.testing.assert_allclose(dbd.biological[rt], arr, rtol=1e-10)

    def test_non_bio_domain_fracs_show_variation(self):
        """Non-bio domain fractions should vary across simulation years when correlation active."""
        rng0 = np.random.default_rng(55)
        losses = rng0.exponential(1e7, (500, 5))
        fracs = {"hab": 0.40, "lice": 0.30, "jellyfish": 0.20, "pathogen": 0.10}
        bio_bd = {rt: losses * f for rt, f in fracs.items()}

        from models.domain_loss_breakdown import build_domain_loss_breakdown
        dbd = build_domain_loss_breakdown(
            losses,
            bio_breakdown=bio_bd,
            domain_correlation=_expert(),
            rng=np.random.default_rng(11),
        )
        # Structural fracs relative to non-bio residual should show variation
        bio_total = sum(dbd.biological.values())
        residual = losses - bio_total
        struct_total = sum(dbd.structural.values())
        # For cells where residual > 0, compute structural share
        mask = residual > 0
        if mask.any():
            shares = struct_total[mask] / residual[mask]
            # Variation should be non-trivial (std > 0.001) for large N
            assert shares.std() > 1e-4, "Structural fraction shows no variation — perturbation inactive?"

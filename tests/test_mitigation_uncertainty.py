"""
Tests for Sprint 2 Part B – Uncertain Mitigation Effectiveness.

Verifies that sample_effectiveness() uses a Beta distribution and that
MitigationAnalyzer.compare() supports use_uncertainty mode while
keeping the deterministic mode backward-compatible.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock

from analysis.mitigation import (
    MitigationAction,
    MitigationAnalyzer,
    PREDEFINED_MITIGATIONS,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_sim(n=1000, t=5, seed=42, mean_loss=10_000_000):
    rng = np.random.default_rng(seed)
    losses = rng.exponential(mean_loss, size=(n, t))
    sim = MagicMock()
    sim.annual_losses = losses
    sim.mean_annual_loss = float(losses.mean())
    sim.var_995 = float(np.percentile(losses.flatten(), 99.5))
    return sim


def _make_bio_bd(sim, fractions=None):
    if fractions is None:
        fractions = {"hab": 0.4, "lice": 0.3, "jellyfish": 0.2, "pathogen": 0.1}
    return {rt: sim.annual_losses * f for rt, f in fractions.items()}


# ── sample_effectiveness ──────────────────────────────────────────────────────

class TestSampleEffectiveness:
    def test_output_shape(self):
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        rng = np.random.default_rng(0)
        samples = action.sample_effectiveness(rng, n_samples=100)
        assert samples.shape == (100,)

    def test_single_sample_shape(self):
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        rng = np.random.default_rng(1)
        samples = action.sample_effectiveness(rng, n_samples=1)
        assert samples.shape == (1,)

    def test_samples_bounded_above_by_combined_loss_reduction(self):
        """Effective reduction should not exceed the nominal combined reduction."""
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        clr = action.combined_loss_reduction
        rng = np.random.default_rng(42)
        samples = action.sample_effectiveness(rng, n_samples=5000)
        assert float(samples.max()) <= clr + 1e-10

    def test_samples_non_negative(self):
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        rng = np.random.default_rng(0)
        samples = action.sample_effectiveness(rng, n_samples=5000)
        assert np.all(samples >= 0.0)

    def test_mean_below_nominal_reduction(self):
        """Beta(8,2) has mean 0.8 so effective reduction ≈ 0.8 × clr."""
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        clr = action.combined_loss_reduction
        rng = np.random.default_rng(99)
        samples = action.sample_effectiveness(rng, n_samples=10_000)
        # Mean should be around 0.80 × clr with 5% tolerance
        assert abs(float(samples.mean()) / clr - 0.80) < 0.05

    def test_default_alpha_beta(self):
        action = MitigationAction(name="x", description="", applies_to_domains=[])
        assert action.effectiveness_alpha == pytest.approx(8.0)
        assert action.effectiveness_beta == pytest.approx(2.0)

    def test_custom_alpha_beta(self):
        action = MitigationAction(
            name="x", description="", applies_to_domains=[],
            probability_reduction=0.5,
            effectiveness_alpha=2.0,
            effectiveness_beta=2.0,  # symmetric → mean = 0.5
        )
        clr = action.combined_loss_reduction
        rng = np.random.default_rng(5)
        samples = action.sample_effectiveness(rng, n_samples=5000)
        # Beta(2,2) has mean = 0.5; effective mean ≈ 0.5 × clr
        assert abs(float(samples.mean()) / clr - 0.5) < 0.05

    def test_zero_reduction_action(self):
        action = MitigationAction(name="x", description="", applies_to_domains=[])
        rng = np.random.default_rng(0)
        samples = action.sample_effectiveness(rng, n_samples=100)
        np.testing.assert_array_equal(samples, 0.0)


# ── MitigationAnalyzer.compare() uncertainty mode ────────────────────────────

class TestUncertaintyCompare:
    def test_deterministic_matches_original_logic(self):
        """use_uncertainty=False must reproduce the original deterministic result."""
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]

        det_scenario = analyzer.compare([action], use_uncertainty=False)
        # The deterministic path uses combined_loss_reduction exactly
        combined_mult = 1.0 - action.combined_loss_reduction
        expected_mean = sim.mean_annual_loss * combined_mult
        assert abs(det_scenario.adjusted_expected_loss - round(expected_mean, 0)) < 100

    def test_uncertainty_mode_returns_scenario(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        rng = np.random.default_rng(7)
        scenario = analyzer.compare([action], use_uncertainty=True, rng=rng)
        assert scenario is not None

    def test_uncertainty_mode_populates_stats(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        rng = np.random.default_rng(7)
        scenario = analyzer.compare([action], use_uncertainty=True, rng=rng)
        assert scenario.effective_reduction_mean is not None
        assert scenario.effective_reduction_p10 is not None
        assert scenario.effective_reduction_p90 is not None

    def test_uncertainty_mode_stats_not_populated_in_det_mode(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        scenario = analyzer.compare([action], use_uncertainty=False)
        assert scenario.effective_reduction_mean is None
        assert scenario.effective_reduction_p10 is None
        assert scenario.effective_reduction_p90 is None

    def test_uncertainty_reduces_losses_on_average(self):
        """Even stochastic scenario should reduce losses (all multipliers ≤ nominal)."""
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        rng = np.random.default_rng(11)
        scenario = analyzer.compare([action], use_uncertainty=True, rng=rng)
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_uncertainty_less_aggressive_than_deterministic(self):
        """
        Stochastic effective reduction has mean < nominal (Beta(8,2) mean=0.8).
        So uncertainty mode should, on average, produce *less* reduction than
        the deterministic mode.
        Run many independent stochastic draws and verify the mean across runs.
        """
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]

        det = analyzer.compare([action], use_uncertainty=False)

        # Run 200 stochastic draws and collect adjusted means
        stochastic_means = []
        for i in range(200):
            rng = np.random.default_rng(i)
            s = analyzer.compare([action], use_uncertainty=True, rng=rng)
            stochastic_means.append(s.adjusted_expected_loss)

        # Mean of stochastic runs should be higher (less reduced) than deterministic
        avg_stochastic = np.mean(stochastic_means)
        assert avg_stochastic >= det.adjusted_expected_loss * 0.95  # allow 5% tolerance

    def test_uncertainty_with_bio_breakdown(self):
        """Uncertainty mode works together with risk-specific bio breakdown."""
        sim = _make_sim()
        bio_bd = _make_bio_bd(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        rng = np.random.default_rng(0)
        scenario = analyzer.compare(
            [action], bio_loss_breakdown=bio_bd,
            use_uncertainty=True, rng=rng,
        )
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss
        assert "jellyfish" in scenario.affected_risk_types

    def test_auto_rng_created_when_none(self):
        """If use_uncertainty=True and rng=None, a fresh RNG is created automatically."""
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        # Should not raise
        scenario = analyzer.compare([action], use_uncertainty=True, rng=None)
        assert scenario is not None
        assert scenario.effective_reduction_mean is not None

    def test_effective_reduction_mean_bounded(self):
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        clr = action.combined_loss_reduction
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        for i in range(20):
            rng = np.random.default_rng(i)
            s = analyzer.compare([action], use_uncertainty=True, rng=rng)
            assert 0.0 <= s.effective_reduction_mean <= clr + 1e-9

    def test_multiple_actions_uncertainty_mode(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        actions = [
            PREDEFINED_MITIGATIONS["lice_barriers"],
            PREDEFINED_MITIGATIONS["jellyfish_mitigation"],
        ]
        rng = np.random.default_rng(55)
        scenario = analyzer.compare(actions, use_uncertainty=True, rng=rng)
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss
        # Two actions → two effective reduction values (one per action)
        # mean/p10/p90 of the two-element list
        assert scenario.effective_reduction_mean is not None

"""
Tests for models/regime_model.py – RiskRegime, RegimeModel, PREDEFINED_REGIMES.
"""

import numpy as np
import pytest

from models.regime_model import (
    RegimeModel,
    RiskRegime,
    PREDEFINED_REGIMES,
)


# ── PREDEFINED_REGIMES ────────────────────────────────────────────────────────

class TestPredefinedRegimes:
    def test_three_regimes(self):
        assert len(PREDEFINED_REGIMES) == 3

    def test_probabilities_sum_to_one(self):
        total = sum(r.probability for r in PREDEFINED_REGIMES.values())
        assert abs(total - 1.0) < 1e-9

    def test_regime_names_present(self):
        assert "normal_year" in PREDEFINED_REGIMES
        assert "high_bio_risk_year" in PREDEFINED_REGIMES
        assert "catastrophic_year" in PREDEFINED_REGIMES

    def test_normal_year_probability(self):
        assert PREDEFINED_REGIMES["normal_year"].probability == pytest.approx(0.75)

    def test_catastrophic_year_multiplier(self):
        assert PREDEFINED_REGIMES["catastrophic_year"].risk_multiplier == pytest.approx(3.5)


# ── RegimeModel default construction ─────────────────────────────────────────

class TestRegimeModelDefault:
    def test_default_uses_predefined(self):
        rm = RegimeModel()
        assert len(rm.regimes) == 3

    def test_names_array_length(self):
        rm = RegimeModel()
        assert len(rm._names) == 3

    def test_probs_sum_to_one(self):
        rm = RegimeModel()
        assert abs(rm._probs.sum() - 1.0) < 1e-9

    def test_all_multipliers_positive(self):
        rm = RegimeModel()
        assert np.all(rm._multipliers > 0)


# ── RegimeModel validation ────────────────────────────────────────────────────

class TestRegimeModelValidation:
    def test_probs_not_summing_to_one_raises(self):
        bad_regimes = {
            "a": RiskRegime(name="a", probability=0.6, risk_multiplier=1.0),
            "b": RiskRegime(name="b", probability=0.6, risk_multiplier=2.0),
        }
        with pytest.raises(ValueError, match="sum to 1"):
            RegimeModel(regimes=bad_regimes)

    def test_negative_probability_raises(self):
        bad_regimes = {
            "a": RiskRegime(name="a", probability=-0.1, risk_multiplier=1.0),
            "b": RiskRegime(name="b", probability=1.1, risk_multiplier=1.0),
        }
        with pytest.raises(ValueError):
            RegimeModel(regimes=bad_regimes)

    def test_empty_regimes_raises(self):
        with pytest.raises(ValueError, match="at least one"):
            RegimeModel(regimes={})

    def test_valid_two_regime_model(self):
        """Two-regime model with probabilities summing to 1 should work."""
        regimes = {
            "normal": RiskRegime(name="normal", probability=0.8, risk_multiplier=1.0),
            "bad": RiskRegime(name="bad", probability=0.2, risk_multiplier=2.0),
        }
        rm = RegimeModel(regimes=regimes)
        assert len(rm.regimes) == 2

    def test_tolerance_for_float_rounding(self):
        """Probabilities that sum to 1 ± 1e-5 should be accepted."""
        regimes = {
            "a": RiskRegime(name="a", probability=1 / 3, risk_multiplier=1.0),
            "b": RiskRegime(name="b", probability=1 / 3, risk_multiplier=1.5),
            "c": RiskRegime(name="c", probability=1 / 3, risk_multiplier=2.0),
        }
        # 1/3 + 1/3 + 1/3 = 0.9999...
        rm = RegimeModel(regimes=regimes)
        assert len(rm.regimes) == 3


# ── sample_regimes ────────────────────────────────────────────────────────────

class TestSampleRegimes:
    def setup_method(self):
        self.rm = RegimeModel()
        self.rng = np.random.default_rng(42)

    def test_shape(self):
        arr = self.rm.sample_regimes(N=100, T=5, rng=self.rng)
        assert arr.shape == (100, 5)

    def test_dtype_is_float(self):
        arr = self.rm.sample_regimes(N=10, T=3, rng=self.rng)
        assert arr.dtype == float

    def test_values_are_valid_multipliers(self):
        """All sampled values must be one of the regime multipliers."""
        arr = self.rm.sample_regimes(N=500, T=5, rng=self.rng)
        valid_multipliers = set(self.rm._multipliers.tolist())
        unique_values = set(np.unique(arr).tolist())
        assert unique_values.issubset(valid_multipliers)

    def test_frequency_roughly_matches_probability(self):
        """In a large sample the fraction of normal-year cells ≈ 0.75."""
        arr = self.rm.sample_regimes(N=5000, T=5, rng=self.rng)
        normal_mult = PREDEFINED_REGIMES["normal_year"].risk_multiplier
        frac_normal = (arr == normal_mult).mean()
        # Allow ±5 percentage points
        assert abs(frac_normal - 0.75) < 0.05

    def test_single_year_single_sim(self):
        arr = self.rm.sample_regimes(N=1, T=1, rng=self.rng)
        assert arr.shape == (1, 1)

    def test_high_risk_multiplier_exceeds_normal(self):
        """High-bio-risk multiplier > normal multiplier."""
        high = PREDEFINED_REGIMES["high_bio_risk_year"].risk_multiplier
        normal = PREDEFINED_REGIMES["normal_year"].risk_multiplier
        assert high > normal


# ── sample_regime_names ───────────────────────────────────────────────────────

class TestSampleRegimeNames:
    def setup_method(self):
        self.rm = RegimeModel()
        self.rng = np.random.default_rng(7)

    def test_shape(self):
        arr = self.rm.sample_regime_names(N=50, T=5, rng=self.rng)
        assert arr.shape == (50, 5)

    def test_values_are_valid_names(self):
        arr = self.rm.sample_regime_names(N=200, T=5, rng=self.rng)
        valid = set(self.rm._names)
        for name in np.unique(arr):
            assert name in valid

    def test_all_regimes_appear_in_large_sample(self):
        arr = self.rm.sample_regime_names(N=2000, T=5, rng=self.rng)
        observed = set(np.unique(arr).tolist())
        assert observed == set(self.rm._names)


# ── from_dict ─────────────────────────────────────────────────────────────────

class TestFromDict:
    def test_basic_two_regime(self):
        d = {
            "low": {"probability": 0.7, "risk_multiplier": 1.0, "description": "Low risk"},
            "high": {"probability": 0.3, "risk_multiplier": 2.5},
        }
        rm = RegimeModel.from_dict(d)
        assert len(rm.regimes) == 2
        assert rm.regimes["low"].risk_multiplier == pytest.approx(1.0)
        assert rm.regimes["high"].risk_multiplier == pytest.approx(2.5)

    def test_description_defaults_to_empty(self):
        d = {
            "a": {"probability": 0.5, "risk_multiplier": 1.0},
            "b": {"probability": 0.5, "risk_multiplier": 2.0},
        }
        rm = RegimeModel.from_dict(d)
        assert rm.regimes["a"].description == ""

    def test_invalid_probabilities_raises(self):
        d = {
            "a": {"probability": 0.6, "risk_multiplier": 1.0},
            "b": {"probability": 0.6, "risk_multiplier": 2.0},
        }
        with pytest.raises(ValueError):
            RegimeModel.from_dict(d)

    def test_sampling_works_after_from_dict(self):
        d = {
            "normal": {"probability": 0.8, "risk_multiplier": 1.0},
            "stressed": {"probability": 0.2, "risk_multiplier": 3.0},
        }
        rm = RegimeModel.from_dict(d)
        rng = np.random.default_rng(99)
        arr = rm.sample_regimes(N=100, T=5, rng=rng)
        assert arr.shape == (100, 5)
        assert set(np.unique(arr).tolist()) <= {1.0, 3.0}

    def test_regime_name_is_set_on_dataclass(self):
        d = {
            "my_regime": {"probability": 1.0, "risk_multiplier": 1.5},
        }
        rm = RegimeModel.from_dict(d)
        assert rm.regimes["my_regime"].name == "my_regime"


# ── Integration: regime multiplier increases expected event count ─────────────

class TestRegimeEffectOnExpectedEvents:
    def test_catastrophic_regime_raises_expected_count(self):
        """
        Verify that sampling multipliers from the regime model actually
        increases the expected event count when passed to np.poisson.
        """
        rng = np.random.default_rng(0)
        rm = RegimeModel()
        N, T = 10_000, 5
        lam = 3.2

        multipliers = rm.sample_regimes(N, T, rng)
        counts_regime = rng.poisson(lam * multipliers)
        counts_static = rng.poisson(lam, size=(N, T))

        # Regime model should produce higher mean (all multipliers ≥ 1.0)
        assert counts_regime.mean() >= counts_static.mean()

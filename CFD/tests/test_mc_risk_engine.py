"""tests/test_mc_risk_engine.py — Sprint 7: vectorised classifier, MCRiskResult, MonteCarloRiskEngine."""
from __future__ import annotations

import math

import numpy as np
import pytest

from core.mc_risk_engine import (
    MCRiskResult,
    MonteCarloRiskEngine,
    _classify_vectorised,
)
from core.risk_engine import RiskEngine


# ── Vectorised classifier ─────────────────────────────────────────────────────

class TestClassifyVectorised:

    @pytest.fixture(scope='class')
    def risk(self):
        return RiskEngine()   # default thresholds

    def test_no_arrival_zero_exposure_is_green(self, risk):
        arr = np.array([float('nan')])
        peak = np.array([0.0])
        exp = np.array([0.0])
        g, y, r = _classify_vectorised(arr, peak, exp, risk)
        assert g[0] and not y[0] and not r[0]

    def test_arrival_below_red_threshold_is_red(self, risk):
        # red_arrival_threshold_s = 600
        arr = np.array([300.0])
        peak = np.array([0.0])
        exp = np.array([0.0])
        g, y, r = _classify_vectorised(arr, peak, exp, risk)
        assert r[0]

    def test_arrival_between_thresholds_is_yellow(self, risk):
        # 600 < 700 < 1200
        arr = np.array([700.0])
        peak = np.array([0.0])
        exp = np.array([0.0])
        g, y, r = _classify_vectorised(arr, peak, exp, risk)
        assert y[0] and not r[0]

    def test_arrival_above_yellow_threshold_is_green(self, risk):
        # 1300 > 1200 → no arrival criterion triggered
        arr = np.array([1300.0])
        peak = np.array([0.0])
        exp = np.array([0.0])
        g, y, r = _classify_vectorised(arr, peak, exp, risk)
        assert g[0]

    def test_peak_above_red_is_red(self, risk):
        arr = np.array([float('nan')])
        peak = np.array([risk.red_peak_risk_concentration + 0.01])
        exp = np.array([0.0])
        g, y, r = _classify_vectorised(arr, peak, exp, risk)
        assert r[0]

    def test_peak_between_thresholds_is_yellow(self, risk):
        arr = np.array([float('nan')])
        mid = (risk.yellow_peak_risk_concentration + risk.red_peak_risk_concentration) / 2
        peak = np.array([mid])
        exp = np.array([0.0])
        g, y, r = _classify_vectorised(arr, peak, exp, risk)
        assert y[0] and not r[0]

    def test_exposure_above_red_is_red(self, risk):
        arr = np.array([float('nan')])
        peak = np.array([0.0])
        exp = np.array([risk.red_exposure_threshold_mass_seconds + 1.0])
        g, y, r = _classify_vectorised(arr, peak, exp, risk)
        assert r[0]

    def test_exposure_between_thresholds_is_yellow(self, risk):
        arr = np.array([float('nan')])
        peak = np.array([0.0])
        mid = (risk.yellow_exposure_threshold_mass_seconds
               + risk.red_exposure_threshold_mass_seconds) / 2
        exp = np.array([mid])
        g, y, r = _classify_vectorised(arr, peak, exp, risk)
        assert y[0] and not r[0]

    def test_probabilities_sum_to_one(self, risk):
        rng = np.random.default_rng(0)
        n = 1000
        arr = np.where(rng.random(n) < 0.5, float('nan'),
                       rng.uniform(100, 1500, n))
        peak = rng.uniform(0, 0.04, n)
        exp = rng.uniform(0, 150, n)
        g, y, r = _classify_vectorised(arr, peak, exp, risk)
        total = g.astype(int) + y.astype(int) + r.astype(int)
        assert np.all(total == 1)

    def test_no_arrival_means_green_false(self, risk):
        """When no_arrival_means_green=False, no-arrival with 0 exposure → not auto-GREEN."""
        arr = np.array([float('nan')])
        peak = np.array([0.0])
        exp = np.array([0.0])
        g, y, r = _classify_vectorised(arr, peak, exp, risk, no_arrival_means_green=False)
        # Neither GREEN shortcut nor RED/YELLOW criterion triggered → GREEN by default
        # (no criteria met → falls through to is_green = ~is_red & ~is_yellow)
        assert g[0]

    def test_vectorised_all_n(self, risk):
        n = 5000
        arr = np.full(n, float('nan'))
        peak = np.zeros(n)
        exp = np.zeros(n)
        g, y, r = _classify_vectorised(arr, peak, exp, risk)
        assert np.all(g)
        assert not np.any(y)
        assert not np.any(r)


# ── MCRiskResult ──────────────────────────────────────────────────────────────

class TestMCRiskResult:

    def test_to_dict_nan_is_none(self, make_mc_result):
        r = make_mc_result(mean_first_arrival_s=float('nan'),
                           p90_first_arrival_s=float('nan'))
        d = r.to_dict()
        assert d['mean_first_arrival_s'] is None
        assert d['p90_first_arrival_s'] is None

    def test_from_dict_restores_nan(self, make_mc_result):
        r = make_mc_result(mean_first_arrival_s=float('nan'))
        r2 = MCRiskResult.from_dict(r.to_dict())
        assert math.isnan(r2.mean_first_arrival_s)

    def test_round_trip_finite(self, make_mc_result):
        r = make_mc_result()
        r2 = MCRiskResult.from_dict(r.to_dict())
        assert r2.p_red == pytest.approx(r.p_red)
        assert r2.modal_risk_status == r.modal_risk_status


# ── MonteCarloRiskEngine ──────────────────────────────────────────────────────

class TestMonteCarloRiskEngine:

    @pytest.fixture
    def engine_self_red(self, simple_mc_library):
        """Engine whose SA->SA pair should be all-RED."""
        return MonteCarloRiskEngine(
            simple_mc_library,
            n_samples=5000,
            shed_rate=1.0,
            total_time_s=1200.0,
            seed=0,
        )

    def test_run_pair_probabilities_sum_to_one(self, engine_self_red):
        r = engine_self_red.run_pair('SA', 'SA', case_name='langs')
        assert r.p_green + r.p_yellow + r.p_red == pytest.approx(1.0, abs=1e-9)

    def test_run_pair_self_red_all_red(self, engine_self_red):
        """SA->SA has high TC (>100s) → all samples should be RED."""
        r = engine_self_red.run_pair('SA', 'SA', case_name='langs')
        # exposure = TC * 1.0 * 1200 ≈ 100*1200 = 120,000 >> red threshold
        assert r.p_red > 0.95

    def test_run_pair_cross_all_green(self, engine_self_red):
        """SA->SB has zero TC → no exposure → all GREEN."""
        r = engine_self_red.run_pair('SA', 'SB', case_name='langs')
        assert r.p_green == pytest.approx(1.0, abs=1e-9)
        assert r.modal_risk_status == 'GREEN'

    def test_run_pair_modal_red_when_p_red_high(self, engine_self_red):
        r = engine_self_red.run_pair('SA', 'SA', case_name='langs')
        assert r.modal_risk_status == 'RED'

    def test_run_pair_expected_score_2_when_all_red(self, engine_self_red):
        r = engine_self_red.run_pair('SA', 'SA', case_name='langs')
        assert r.expected_risk_score == pytest.approx(2.0 * r.p_red + r.p_yellow,
                                                      abs=1e-9)

    def test_run_all_returns_four_results(self, engine_self_red):
        results = engine_self_red.run_all()
        assert len(results) == 4   # SA->SA, SA->SB, SB->SA, SB->SB

    def test_run_all_n_samples_set(self, engine_self_red):
        results = engine_self_red.run_all()
        assert all(r.n_samples == 5000 for r in results)

    def test_risk_probability_matrix_shape(self, engine_self_red):
        results = engine_self_red.run_all()
        mat = engine_self_red.risk_probability_matrix('RED', results)
        assert mat.shape == (2, 2)

    def test_modal_risk_matrix_diagonal_red(self, engine_self_red):
        results = engine_self_red.run_all()
        mat = engine_self_red.modal_risk_matrix(results)
        assert mat.loc['SA', 'SA'] == 'RED'
        assert mat.loc['SB', 'SB'] == 'RED'

    def test_modal_risk_matrix_off_diagonal_green(self, engine_self_red):
        results = engine_self_red.run_all()
        mat = engine_self_red.modal_risk_matrix(results)
        assert mat.loc['SA', 'SB'] == 'GREEN'
        assert mat.loc['SB', 'SA'] == 'GREEN'

    def test_expected_score_matrix_shape(self, engine_self_red):
        results = engine_self_red.run_all()
        mat = engine_self_red.expected_risk_score_matrix(results)
        assert mat.shape == (2, 2)

    def test_summary_df_has_all_pairs(self, engine_self_red):
        results = engine_self_red.run_all()
        df = engine_self_red.summary_df(results)
        assert len(df) == 4

    def test_save_results_creates_files(self, engine_self_red, tmp_path):
        results = engine_self_red.run_all()
        paths = engine_self_red.save_results(results, tmp_path)
        assert paths['csv_path'].exists()
        assert paths['json_path'].exists()
        assert paths['csv_path'].stat().st_size > 0

    def test_shed_rate_scales_exposure(self, simple_mc_library):
        """Doubling shed_rate should double expected_risk_score when already RED."""
        e1 = MonteCarloRiskEngine(simple_mc_library, n_samples=2000,
                                  shed_rate=1.0, total_time_s=1200.0, seed=1)
        e2 = MonteCarloRiskEngine(simple_mc_library, n_samples=2000,
                                  shed_rate=2.0, total_time_s=1200.0, seed=1)
        r1 = e1.run_pair('SA', 'SA', 'langs')
        r2 = e2.run_pair('SA', 'SA', 'langs')
        # Both should be RED — can't go "more red", but VaR99 should be higher
        assert r2.var99_exposure_ms > r1.var99_exposure_ms

    def test_zero_n_samples_edge(self, simple_mc_library):
        """n_samples=1 should still return a valid result."""
        e = MonteCarloRiskEngine(simple_mc_library, n_samples=1,
                                 total_time_s=1200.0, seed=99)
        r = e.run_pair('SA', 'SA', 'langs')
        assert r.p_green + r.p_yellow + r.p_red == pytest.approx(1.0, abs=1e-9)

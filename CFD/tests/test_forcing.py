"""tests/test_forcing.py — Sprint 4: CurrentForcing tests."""
from __future__ import annotations

import math
import textwrap

import numpy as np
import pytest

from core.forcing import CurrentForcing


# ── Construction ──────────────────────────────────────────────────────────────

class TestCurrentForcingConstruction:

    def test_basic_construction(self):
        times = np.array([0.0, 600.0, 1200.0])
        u = np.array([0.2, 0.3, 0.1])
        v = np.array([0.0, 0.05, -0.05])
        cf = CurrentForcing(times, u, v, label='test')
        assert cf.label == 'test'
        assert len(cf.times_s) == 3

    def test_monotonicity_required(self):
        with pytest.raises(ValueError, match='monoton'):
            CurrentForcing(np.array([0.0, 600.0, 300.0]),
                           np.array([0.1, 0.1, 0.1]),
                           np.array([0.0, 0.0, 0.0]))

    def test_shape_mismatch_raises(self):
        with pytest.raises(ValueError):
            CurrentForcing(np.array([0.0, 600.0]),
                           np.array([0.1, 0.2, 0.3]),
                           np.array([0.0, 0.0]))

    def test_constant_classmethod(self):
        cf = CurrentForcing.constant(u=0.3, v=0.1, duration_s=1200.0)
        assert math.isclose(cf.speed_at(0.0), math.hypot(0.3, 0.1), rel_tol=1e-9)
        assert math.isclose(cf.speed_at(600.0), math.hypot(0.3, 0.1), rel_tol=1e-9)
        assert math.isclose(cf.speed_at(1200.0), math.hypot(0.3, 0.1), rel_tol=1e-9)

    def test_from_named_case_langs(self):
        cf = CurrentForcing.from_named_case('langs', U_inf=0.5, duration_s=1200.0)
        u, v = cf.velocity_at(600.0)
        # 'langs' is along-shore (east): u dominant, v small
        assert abs(u) > abs(v)

    def test_from_named_case_tverrs(self):
        cf = CurrentForcing.from_named_case('tverrs', U_inf=0.5, duration_s=1200.0)
        u, v = cf.velocity_at(600.0)
        # 'tverrs' is cross-shore: v dominant
        assert abs(v) > abs(u)


# ── Interpolation ─────────────────────────────────────────────────────────────

class TestCurrentForcingInterpolation:

    @pytest.fixture
    def linear_forcing(self):
        return CurrentForcing(
            times_s=np.array([0.0, 1000.0]),
            u=np.array([0.0, 1.0]),
            v=np.array([0.0, 0.0]),
        )

    def test_velocity_at_start(self, linear_forcing):
        u, v = linear_forcing.velocity_at(0.0)
        assert math.isclose(u, 0.0, abs_tol=1e-12)

    def test_velocity_at_end(self, linear_forcing):
        u, v = linear_forcing.velocity_at(1000.0)
        assert math.isclose(u, 1.0, rel_tol=1e-9)

    def test_velocity_at_midpoint(self, linear_forcing):
        u, v = linear_forcing.velocity_at(500.0)
        assert math.isclose(u, 0.5, rel_tol=1e-9)

    def test_speed_at(self, linear_forcing):
        s = linear_forcing.speed_at(500.0)
        assert math.isclose(s, 0.5, rel_tol=1e-9)

    def test_direction_at_zero_speed_fallback(self):
        cf = CurrentForcing.constant(u=0.0, v=0.0, duration_s=100.0)
        d = cf.direction_at(50.0)
        # Should return a unit fallback vector, not raise
        assert np.linalg.norm(d) == pytest.approx(1.0, abs=1e-6)

    def test_extrapolation_clamps_to_boundary(self, linear_forcing):
        # Beyond the end should clamp to last value
        u_after, _ = linear_forcing.velocity_at(5000.0)
        assert math.isclose(u_after, 1.0, rel_tol=1e-9)


# ── Statistics ────────────────────────────────────────────────────────────────

class TestCurrentForcingStats:

    @pytest.fixture
    def symmetric_forcing(self):
        # u oscillates, v=0 → mean_speed = mean of abs(u interpolated)
        return CurrentForcing(
            times_s=np.array([0.0, 600.0, 1200.0]),
            u=np.array([0.3, 0.3, 0.3]),
            v=np.array([0.0, 0.0, 0.0]),
        )

    def test_mean_speed_positive(self, symmetric_forcing):
        assert symmetric_forcing.mean_speed() > 0.0

    def test_dominant_direction_unit(self, symmetric_forcing):
        d = symmetric_forcing.dominant_direction()
        assert np.linalg.norm(d) == pytest.approx(1.0, abs=1e-6)

    def test_summary_stats_keys(self, symmetric_forcing):
        stats = symmetric_forcing.summary_stats()
        for key in ('label', 'n_points', 'duration_s', 'mean_speed_m_s'):
            assert key in stats

    def test_duration(self, symmetric_forcing):
        stats = symmetric_forcing.summary_stats()
        assert math.isclose(stats['duration_s'], 1200.0, rel_tol=1e-9)


# ── CSV round-trip ────────────────────────────────────────────────────────────

class TestCurrentForcingCSV:

    def test_format_a_round_trip(self, tmp_path):
        cf = CurrentForcing(
            times_s=np.array([0.0, 300.0, 600.0]),
            u=np.array([0.2, 0.3, 0.1]),
            v=np.array([0.05, -0.05, 0.0]),
        )
        path = tmp_path / 'currents.csv'
        cf.to_csv(path, fmt='cartesian')
        cf2 = CurrentForcing.from_csv(path)
        assert len(cf2.times_s) == 3
        u2, v2 = cf2.velocity_at(300.0)
        assert math.isclose(u2, 0.3, rel_tol=1e-6)
        assert math.isclose(v2, -0.05, rel_tol=1e-6)

    def test_format_b_polar(self, tmp_path):
        path = tmp_path / 'polar.csv'
        # Write Format B manually: oceanographic convention 0=N 90=E toward
        path.write_text(
            'time_s,speed_m_s,direction_deg\n'
            '0,0.3,90\n'      # eastward (u=0.3, v=0)
            '600,0.3,90\n',
            encoding='utf-8',
        )
        cf = CurrentForcing.from_csv(path)
        u, v = cf.velocity_at(0.0)
        # Eastward → u≈0.3, v≈0
        assert abs(u) == pytest.approx(0.3, abs=1e-3)
        assert abs(v) < 0.01

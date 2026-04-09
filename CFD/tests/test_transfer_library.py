"""tests/test_transfer_library.py — Sprint 6: distribution fitting, EnsembleLibrary, MCTransferLibrary."""
from __future__ import annotations

import math

import numpy as np
import pytest

from core.transfer_library import (
    TransferDistribution,
    EnsembleLibrary,
    MCTransferLibrary,
    EnsembleRunner,
    _fit_distribution,
)


# ── _fit_distribution ─────────────────────────────────────────────────────────

class TestFitDistribution:

    def test_all_zero_gives_zero_type(self):
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s',
                              [0.0, 0.0, 0.0])
        assert d.dist_type == 'zero'
        assert d.nonzero_count == 0

    def test_nonzero_gives_lognormal(self):
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s',
                              [100.0, 110.0, 95.0])
        assert d.dist_type == 'lognormal'
        assert d.nonzero_count == 3
        assert math.isfinite(d.lognormal_mu)

    def test_zero_fraction_calculated(self):
        # 2 of 5 are zero → zero_fraction = 0.4
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s',
                              [0.0, 100.0, 110.0, 0.0, 95.0])
        assert d.zero_fraction == pytest.approx(0.4, rel=1e-9)

    def test_single_nonzero_sigma_nan(self):
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s',
                              [0.0, 0.0, 100.0])
        assert d.dist_type == 'lognormal'
        assert math.isnan(d.lognormal_sigma)   # only 1 nonzero → can't compute std

    def test_lognormal_mu_correct(self):
        vals = [math.e, math.e, math.e]   # log(e) = 1 → mu = 1
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s', vals)
        assert d.lognormal_mu == pytest.approx(1.0, rel=1e-6)

    def test_mean_percentiles_computed(self):
        vals = [100.0, 200.0, 150.0, 180.0, 120.0]
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s', vals)
        assert d.mean == pytest.approx(np.mean(vals), rel=1e-9)
        assert d.p50 == pytest.approx(np.percentile(vals, 50), rel=1e-9)

    def test_nan_values_treated_as_zero_for_tc(self):
        """NaN in TC values should be treated as 0 (no transfer)."""
        vals = [float('nan'), 100.0, 110.0]
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s', vals)
        assert d.zero_fraction == pytest.approx(1/3, rel=1e-6)

    def test_target_net_area_stored(self):
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s',
                              [100.0], target_net_plan_area_m2=2827.0)
        assert d.target_net_plan_area_m2 == pytest.approx(2827.0)


# ── TransferDistribution.sample ───────────────────────────────────────────────

class TestTransferDistributionSample:
    rng = np.random.default_rng(0)

    def test_zero_type_returns_zeros(self):
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s',
                              [0.0, 0.0, 0.0])
        s = d.sample(1000, self.rng)
        assert np.all(s == 0.0)

    def test_lognormal_correct_shape(self):
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s',
                              [100.0, 110.0, 95.0, 105.0, 108.0])
        s = d.sample(5000, self.rng)
        assert s.shape == (5000,)
        assert np.all(s >= 0.0)

    def test_zero_inflated_fraction(self):
        vals = [0.0, 100.0, 110.0, 0.0, 95.0]   # zero_fraction = 0.4
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s', vals)
        s = d.sample(20_000, self.rng)
        observed_zero = (s == 0.0).mean()
        assert 0.35 < observed_zero < 0.45, f"Expected ~0.4, got {observed_zero:.3f}"

    def test_lognormal_mean_reasonable(self):
        vals = [100.0, 110.0, 95.0, 105.0, 100.0]
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s', vals)
        s = d.sample(50_000, self.rng)
        # E[X] = exp(mu + sigma²/2); mean should be near 102
        assert 80.0 < s.mean() < 130.0, f"mean={s.mean():.2f}"


# ── TransferDistribution serialisation ───────────────────────────────────────

class TestTransferDistributionSerialisation:

    def test_to_dict_nan_becomes_none(self):
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s', [0.0])
        dd = d.to_dict()
        assert dd['lognormal_mu'] is None
        assert dd['lognormal_sigma'] is None

    def test_from_dict_round_trip(self):
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s',
                              [100.0, 110.0, 95.0])
        d2 = TransferDistribution.from_dict(d.to_dict())
        assert d2.dist_type == d.dist_type
        assert d2.lognormal_mu == pytest.approx(d.lognormal_mu, rel=1e-12)

    def test_from_dict_backward_compat_missing_area(self):
        """Older JSON without target_net_plan_area_m2 should load with default 1.0."""
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s', [100.0])
        dd = d.to_dict()
        del dd['target_net_plan_area_m2']
        d2 = TransferDistribution.from_dict(dd)
        assert d2.target_net_plan_area_m2 == pytest.approx(1.0)

    def test_empirical_values_stored(self):
        vals = [100.0, 110.0, 95.0]
        d = _fit_distribution('A', 'B', 'test', 'transfer_coefficient_s', vals)
        assert len(d.empirical) == 3


# ── MCTransferLibrary ─────────────────────────────────────────────────────────

class TestMCTransferLibrary:
    rng = np.random.default_rng(42)

    def test_sample_tc_shape(self, simple_mc_library):
        s = simple_mc_library.sample_tc('SA', 'SA', 1000, self.rng)
        assert s.shape == (1000,)

    def test_sample_tc_self_pair_positive(self, simple_mc_library):
        s = simple_mc_library.sample_tc('SA', 'SA', 5000, self.rng)
        assert s.mean() > 50.0

    def test_sample_tc_zero_pair_all_zero(self, simple_mc_library):
        s = simple_mc_library.sample_tc('SA', 'SB', 1000, self.rng)
        assert np.all(s == 0.0)

    def test_sample_peak_shape(self, simple_mc_library):
        s = simple_mc_library.sample_peak('SA', 'SA', 500, self.rng)
        assert s.shape == (500,)

    def test_sample_arrival_finite_for_self(self, simple_mc_library):
        s = simple_mc_library.sample_arrival('SA', 'SA', 5000, self.rng)
        assert np.isfinite(s).mean() > 0.9   # mostly finite

    def test_sample_arrival_nan_for_zero_pair(self, simple_mc_library):
        s = simple_mc_library.sample_arrival('SA', 'SB', 1000, self.rng)
        assert np.all(np.isnan(s))   # zero dist → all NaN

    def test_unknown_pair_returns_zeros(self, simple_mc_library):
        s = simple_mc_library.sample_tc('XX', 'YY', 100, self.rng)
        assert np.all(s == 0.0)

    def test_expected_dose_matrix_shape(self, simple_mc_library):
        dm = simple_mc_library.expected_dose_matrix(shed_rate=1.0)
        assert dm.shape == (2, 2)
        assert 'SA' in dm.index
        assert 'SB' in dm.columns

    def test_expected_dose_scales_with_shed_rate(self, simple_mc_library):
        dm1 = simple_mc_library.expected_dose_matrix(shed_rate=1.0)
        dm2 = simple_mc_library.expected_dose_matrix(shed_rate=2.0)
        assert dm2.loc['SA', 'SA'] == pytest.approx(2.0 * dm1.loc['SA', 'SA'], rel=1e-9)

    def test_risk_summary_df_columns(self, simple_mc_library):
        df = simple_mc_library.risk_summary_df()
        for col in ('source_site_id', 'target_site_id', 'mean_tc_s', 'zero_fraction'):
            assert col in df.columns

    def test_save_load_round_trip(self, simple_mc_library, tmp_path):
        simple_mc_library.save(tmp_path)
        mc2 = MCTransferLibrary.load(tmp_path)
        assert mc2.n_ensemble == simple_mc_library.n_ensemble
        assert len(mc2.distributions) == len(simple_mc_library.distributions)
        # Check a distribution is faithfully restored
        d_orig = simple_mc_library._index[('SA', 'SA', 'langs', 'transfer_coefficient_s')]
        d_loaded = mc2._index[('SA', 'SA', 'langs', 'transfer_coefficient_s')]
        assert d_loaded.lognormal_mu == pytest.approx(d_orig.lognormal_mu, rel=1e-9)

    def test_save_creates_both_files(self, simple_mc_library, tmp_path):
        paths = simple_mc_library.save(tmp_path)
        assert paths['json_path'].exists()
        assert paths['csv_path'].exists()
        assert paths['json_path'].stat().st_size > 0


# ── EnsembleLibrary.fit_distributions ────────────────────────────────────────

class TestEnsembleLibraryFitting:

    def _make_run(self, tc_val, rng_seed=0):
        """Build a minimal TransferLibrary with fixed TC values."""
        from core.transfer_engine import TransferResult, TransferLibrary
        r = TransferResult(
            source_site_id='SA', target_site_id='SA',
            source_net_name='Net A', target_net_name='Net A',
            case_name='langs',
            transfer_coefficient_s=tc_val,
            peak_mass_fraction=0.05,
            first_arrival_s=30.0,
            total_exposure_mass_seconds=tc_val * 1200.0,
            total_shed_mass=1200.0,
            risk_status='RED',
            forcing_mean_speed_m_s=0.3,
            forcing_dir_deg=90.0,
            target_net_plan_area_m2=2827.0,
        )
        return TransferLibrary([r], scenario_name='test')

    def test_fit_three_runs(self):
        runs = [self._make_run(tc) for tc in [100.0, 110.0, 95.0]]
        ens = EnsembleLibrary(runs, scenario_name='test')
        dists = ens.fit_distributions()
        tc_dists = [d for d in dists
                    if d.metric == 'transfer_coefficient_s'
                    and d.source_site_id == 'SA' and d.target_site_id == 'SA']
        assert len(tc_dists) == 1
        d = tc_dists[0]
        assert d.dist_type == 'lognormal'
        assert d.nonzero_count == 3
        assert d.mean == pytest.approx(np.mean([100.0, 110.0, 95.0]), rel=1e-6)

    def test_to_mc_library(self):
        runs = [self._make_run(tc) for tc in [100.0, 110.0, 95.0]]
        ens = EnsembleLibrary(runs, scenario_name='test')
        mc = ens.to_mc_library()
        assert isinstance(mc, MCTransferLibrary)
        assert mc.n_ensemble == 3
        assert len(mc.distributions) > 0

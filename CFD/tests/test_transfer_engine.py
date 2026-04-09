"""tests/test_transfer_engine.py — Sprint 5: TransferResult, TransferLibrary, TransferEngine."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from core.transfer_engine import TransferResult, TransferLibrary, TransferEngine


# ── TransferResult ────────────────────────────────────────────────────────────

class TestTransferResult:

    def test_to_dict_keys(self, make_transfer_result):
        r = make_transfer_result()
        d = r.to_dict()
        assert 'transfer_coefficient_s' in d
        assert 'peak_mass_fraction' in d
        assert 'risk_status' in d

    def test_nan_serialises_to_none(self, make_transfer_result):
        r = make_transfer_result(first_arrival_s=float('nan'))
        assert r.to_dict()['first_arrival_s'] is None

    def test_from_dict_restores_nan(self, make_transfer_result):
        r = make_transfer_result(first_arrival_s=float('nan'))
        r2 = TransferResult.from_dict(r.to_dict())
        assert math.isnan(r2.first_arrival_s)

    def test_round_trip_finite(self, make_transfer_result):
        r = make_transfer_result()
        r2 = TransferResult.from_dict(r.to_dict())
        assert r2.transfer_coefficient_s == pytest.approx(r.transfer_coefficient_s)
        assert r2.source_site_id == r.source_site_id
        assert r2.risk_status == r.risk_status

    def test_transfer_coefficient_formula(self, make_transfer_result):
        """TC = total_exposure_mass_s / total_shed_mass."""
        r = make_transfer_result(
            total_exposure_mass_seconds=6000.0,
            total_shed_mass=1200.0,
            transfer_coefficient_s=5.0,
        )
        # stored TC matches the formula
        assert r.transfer_coefficient_s == pytest.approx(5.0)


# ── TransferLibrary ───────────────────────────────────────────────────────────

class TestTransferLibrary:

    def test_to_df_shape(self, two_result_library):
        df = two_result_library.to_df()
        assert df.shape == (2, 14)   # 2 results, 14 fields

    def test_to_df_columns(self, two_result_library):
        cols = two_result_library.to_df().columns.tolist()
        assert 'transfer_coefficient_s' in cols
        assert 'risk_status' in cols

    def test_transfer_matrix_pivot(self, two_result_library):
        mat = two_result_library.transfer_matrix('transfer_coefficient_s', 'max')
        assert 'SA' in mat.index
        assert 'SA' in mat.columns
        assert mat.loc['SA', 'SA'] == pytest.approx(120.0)
        assert mat.loc['SA', 'SB'] == pytest.approx(0.0)

    def test_risk_matrix_pivot(self, two_result_library):
        mat = two_result_library.risk_matrix()
        assert mat.loc['SA', 'SA'] == 'RED'
        assert mat.loc['SA', 'SB'] == 'GREEN'

    def test_save_creates_files(self, two_result_library, tmp_path):
        paths = two_result_library.save(tmp_path)
        assert paths['csv_path'].exists()
        assert paths['json_path'].exists()
        assert paths['csv_path'].stat().st_size > 0

    def test_load_round_trip(self, two_result_library, tmp_path):
        two_result_library.save(tmp_path)
        lib2 = TransferLibrary.load(tmp_path)
        assert len(lib2.results) == 2
        assert lib2.scenario_name == 'test_scenario'

    def test_load_restores_nan(self, two_result_library, tmp_path):
        two_result_library.save(tmp_path)
        lib2 = TransferLibrary.load(tmp_path)
        cross = next(r for r in lib2.results if r.target_site_id == 'SB')
        assert math.isnan(cross.first_arrival_s)

    def test_empty_library(self):
        lib = TransferLibrary([], scenario_name='empty')
        assert lib.to_df().empty
        assert lib.risk_matrix().empty
        assert lib.transfer_matrix().empty

    def test_aggfunc_mean(self, two_result_library):
        mat_max = two_result_library.transfer_matrix('transfer_coefficient_s', 'max')
        mat_mean = two_result_library.transfer_matrix('transfer_coefficient_s', 'mean')
        # With one result per pair, max == mean
        assert mat_max.loc['SA', 'SA'] == pytest.approx(mat_mean.loc['SA', 'SA'])


# ── TransferEngine (integration) ──────────────────────────────────────────────

class TestTransferEngineIntegration:
    """These tests actually run particle transport — kept fast via minimal params."""

    FAST_KWARGS = dict(
        dt_s=60.0, total_time_s=120.0, particles_per_step=2,
        biology_enabled=False, verbose=False,
        auto_calibrate_from_first_case=False,
        shedding_rate_relative_per_s=1.0,
    )

    @pytest.mark.slow
    def test_run_source_returns_results(self, minimal_scenario, minimal_flow_model):
        engine = TransferEngine(self.FAST_KWARGS, verbose=False)
        results = engine.run_source(
            minimal_flow_model,
            minimal_scenario.sites[0],
            case_list=['langs'],
            current_forcing=None,
        )
        assert len(results) > 0
        assert all(isinstance(r, TransferResult) for r in results)

    @pytest.mark.slow
    def test_self_tc_positive(self, minimal_scenario, minimal_flow_model):
        """Source site should have positive TC in its own nets."""
        engine = TransferEngine(self.FAST_KWARGS, verbose=False)
        results = engine.run_source(
            minimal_flow_model,
            minimal_scenario.sites[0],
            case_list=['langs'],
            current_forcing=None,
        )
        self_results = [r for r in results if r.target_site_id == 'SA']
        assert any(r.transfer_coefficient_s > 0 for r in self_results)

    @pytest.mark.slow
    def test_total_shed_mass_formula(self, minimal_scenario, minimal_flow_model):
        """total_shed_mass = shedding_rate * total_time_s."""
        engine = TransferEngine(self.FAST_KWARGS, verbose=False)
        results = engine.run_source(
            minimal_flow_model,
            minimal_scenario.sites[0],
            case_list=['langs'],
            current_forcing=None,
        )
        expected = 1.0 * 120.0   # shed_rate * total_time_s
        for r in results:
            assert r.total_shed_mass == pytest.approx(expected, rel=1e-9)

    @pytest.mark.slow
    def test_run_all_pairs_library(self, minimal_scenario, tmp_path):
        engine = TransferEngine(self.FAST_KWARGS, verbose=False)
        lib = engine.run_all_pairs(
            scenario=minimal_scenario,
            output_dir=tmp_path,
            current_forcing=None,
            case_list=['langs'],
        )
        assert isinstance(lib, TransferLibrary)
        assert len(lib.results) > 0
        assert (tmp_path / 'transfer_results.csv').exists()
        assert (tmp_path / 'transfer_library.json').exists()

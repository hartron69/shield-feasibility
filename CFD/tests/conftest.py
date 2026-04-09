"""
conftest.py — Shared pytest fixtures for CFD AquaGuard test suite.

All fixtures build minimal in-memory objects — no file I/O, no full
particle simulation — so the fixture setup is instantaneous.

For integration tests that require actual particle runs see the individual
test files; those are marked @pytest.mark.slow.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pytest

# Ensure CFD root is on sys.path so `core` is importable
_CFD_ROOT = Path(__file__).resolve().parent.parent
if str(_CFD_ROOT) not in sys.path:
    sys.path.insert(0, str(_CFD_ROOT))


# ── Geometry fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def straight_coast():
    from core.geometry import StraightCoastline
    return StraightCoastline(y_coast=-150.0)


@pytest.fixture(scope='session')
def net_a():
    from core.geometry import Net
    return Net(name='Net A', center=(0.0, 0.0), radius=30.0,
               depth=20.0, solidity=0.20)


@pytest.fixture(scope='session')
def net_b():
    from core.geometry import Net
    return Net(name='Net B', center=(250.0, 0.0), radius=30.0,
               depth=20.0, solidity=0.20)


@pytest.fixture(scope='session')
def site_a(net_a):
    from core.geometry import Site
    return Site(site_id='SA', name='Site A', x=0.0, y=0.0, nets=[net_a])


@pytest.fixture(scope='session')
def site_b(net_b):
    from core.geometry import Site
    return Site(site_id='SB', name='Site B', x=250.0, y=0.0, nets=[net_b])


@pytest.fixture(scope='session')
def minimal_scenario(site_a, site_b, straight_coast):
    """Two-site, two-net scenario using a StraightCoastline."""
    from core.geometry import FjordScenario
    sites = [site_a, site_b]
    domain = FjordScenario.auto_domain(sites, straight_coast, padding=80.0)
    return FjordScenario(
        name='test_scenario',
        sites=sites,
        coastline=straight_coast,
        domain=domain,
        pathogen_source={
            'source_mode': 'infected_net',
            'source_net_name': 'Net A',
            'shedding_rate_relative_per_s': 1.0,
            'source_infectivity': 1.0,
            'biology_enabled': False,    # no inactivation for deterministic tests
        },
        forcing={'mode': 'named_cases', 'cases': ['langs'], 'U_inf': 0.30},
    )


@pytest.fixture(scope='session')
def minimal_flow_model(minimal_scenario, tmp_path_factory):
    """Flow model built from minimal_scenario."""
    out = tmp_path_factory.mktemp('flow_model')
    return minimal_scenario.build_flow_model(U_inf=0.30, output_dir=out)


# ── TransferResult / TransferLibrary fixtures ─────────────────────────────────

@pytest.fixture
def make_transfer_result():
    """Factory for TransferResult with sensible defaults."""
    from core.transfer_engine import TransferResult

    def _make(**overrides):
        defaults = dict(
            source_site_id='SA', target_site_id='SA',
            source_net_name='Net A', target_net_name='Net A',
            case_name='langs',
            transfer_coefficient_s=120.0,
            peak_mass_fraction=0.10,
            first_arrival_s=60.0,
            total_exposure_mass_seconds=144000.0,
            total_shed_mass=1200.0,
            risk_status='RED',
            forcing_mean_speed_m_s=0.30,
            forcing_dir_deg=90.0,
            target_net_plan_area_m2=2827.0,
        )
        defaults.update(overrides)
        return TransferResult(**defaults)
    return _make


@pytest.fixture
def two_result_library(make_transfer_result):
    """TransferLibrary with one self-pair (RED) and one cross-pair (GREEN)."""
    from core.transfer_engine import TransferLibrary
    r_self = make_transfer_result()
    r_cross = make_transfer_result(
        target_site_id='SB', target_net_name='Net B',
        transfer_coefficient_s=0.0, peak_mass_fraction=0.0,
        first_arrival_s=float('nan'), total_exposure_mass_seconds=0.0,
        risk_status='GREEN',
    )
    return TransferLibrary([r_self, r_cross], scenario_name='test_scenario')


# ── MCTransferLibrary fixtures ────────────────────────────────────────────────

def _make_dist(src, tgt, metric, values, area=2827.0):
    from core.transfer_library import _fit_distribution
    return _fit_distribution(src, tgt, 'langs', metric, values,
                             target_net_plan_area_m2=area)


@pytest.fixture(scope='session')
def simple_mc_library():
    """
    MCTransferLibrary with four (src, tgt) pairs and three metrics,
    built from synthetic values — no simulation required.
    """
    from core.transfer_library import MCTransferLibrary, _fit_distribution

    dists = []
    # SA->SA : high TC (RED)
    for metric, vals in [
        ('transfer_coefficient_s', [100.0, 110.0, 95.0, 105.0, 108.0]),
        ('peak_mass_fraction',     [0.08,  0.09,  0.07, 0.085, 0.088]),
        ('first_arrival_s',        [30.0,  25.0,  35.0, 28.0,  32.0]),
    ]:
        dists.append(_fit_distribution('SA', 'SA', 'langs', metric, vals,
                                       target_net_plan_area_m2=2827.0))

    # SA->SB : zero TC (GREEN)
    for metric, vals in [
        ('transfer_coefficient_s', [0.0, 0.0, 0.0, 0.0, 0.0]),
        ('peak_mass_fraction',     [0.0, 0.0, 0.0, 0.0, 0.0]),
        ('first_arrival_s',        [float('nan')] * 5),
    ]:
        dists.append(_fit_distribution('SA', 'SB', 'langs', metric, vals,
                                       target_net_plan_area_m2=2827.0))

    # SB->SA : zero TC (GREEN)
    for metric, vals in [
        ('transfer_coefficient_s', [0.0, 0.0, 0.0, 0.0, 0.0]),
        ('peak_mass_fraction',     [0.0, 0.0, 0.0, 0.0, 0.0]),
        ('first_arrival_s',        [float('nan')] * 5),
    ]:
        dists.append(_fit_distribution('SB', 'SA', 'langs', metric, vals,
                                       target_net_plan_area_m2=2827.0))

    # SB->SB : high TC (RED)
    for metric, vals in [
        ('transfer_coefficient_s', [115.0, 120.0, 112.0, 118.0, 116.0]),
        ('peak_mass_fraction',     [0.09,  0.10,  0.085, 0.095, 0.092]),
        ('first_arrival_s',        [20.0,  18.0,  22.0,  19.0,  21.0]),
    ]:
        dists.append(_fit_distribution('SB', 'SB', 'langs', metric, vals,
                                       target_net_plan_area_m2=2827.0))

    return MCTransferLibrary(
        distributions=dists,
        scenario_name='test_scenario',
        n_ensemble=5,
        metadata={'version': 'test'},
    )


# ── MCRiskResult fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def make_mc_result():
    """Factory for MCRiskResult."""
    from core.mc_risk_engine import MCRiskResult

    def _make(**overrides):
        defaults = dict(
            source_site_id='SA', target_site_id='SA',
            case_name='langs', n_samples=1000,
            p_green=0.0, p_yellow=0.0, p_red=1.0,
            modal_risk_status='RED', expected_risk_score=2.0,
            mean_tc_s=105.0, p10_tc_s=95.0, p50_tc_s=105.0, p90_tc_s=115.0,
            mean_exposure_ms=126000.0, var95_exposure_ms=130000.0,
            var99_exposure_ms=135000.0,
            mean_first_arrival_s=30.0, p_no_arrival=0.0, p90_first_arrival_s=35.0,
        )
        defaults.update(overrides)
        return MCRiskResult(**defaults)
    return _make


@pytest.fixture
def four_mc_results(make_mc_result):
    """Four MCRiskResults: SA->SA RED, SA->SB GREEN, SB->SA GREEN, SB->SB RED."""
    return [
        make_mc_result(source_site_id='SA', target_site_id='SA'),
        make_mc_result(
            source_site_id='SA', target_site_id='SB',
            p_green=1.0, p_yellow=0.0, p_red=0.0,
            modal_risk_status='GREEN', expected_risk_score=0.0,
            mean_tc_s=0.0, p10_tc_s=0.0, p50_tc_s=0.0, p90_tc_s=0.0,
            mean_exposure_ms=0.0, var95_exposure_ms=0.0, var99_exposure_ms=0.0,
            mean_first_arrival_s=float('nan'), p_no_arrival=1.0,
            p90_first_arrival_s=float('nan'),
        ),
        make_mc_result(
            source_site_id='SB', target_site_id='SA',
            p_green=1.0, p_yellow=0.0, p_red=0.0,
            modal_risk_status='GREEN', expected_risk_score=0.0,
            mean_tc_s=0.0, p10_tc_s=0.0, p50_tc_s=0.0, p90_tc_s=0.0,
            mean_exposure_ms=0.0, var95_exposure_ms=0.0, var99_exposure_ms=0.0,
            mean_first_arrival_s=float('nan'), p_no_arrival=1.0,
            p90_first_arrival_s=float('nan'),
        ),
        make_mc_result(source_site_id='SB', target_site_id='SB',
                       mean_tc_s=116.0, p50_tc_s=116.0, p90_tc_s=121.0,
                       mean_first_arrival_s=20.0),
    ]

"""
Tests for backend/services/operator_builder.py

Covers:
* Risk parameter scaling with exposure (tiv_ratio)
* Financial ratio derivation from revenue
* Equipment/infrastructure allocation without n-scaling inflation
* Biomass + revenue consistency across sites
* MC differentiates operators of different size
* AllocationSummary fields populated correctly
* Site cloning: processing sites not cloned when n_sites > template_n_sites
"""

import math

import numpy as np
import pytest

from backend.schemas import OperatorProfileInput
from backend.services.operator_builder import (
    _TEMPLATE_EXPOSURE,
    _TEMPLATE_EVENTS,
    _TEMPLATE_N_SITES,
    _TEMPLATE_SEVERITY,
    _EBITDA_MARGIN,
    _EQUITY_RATIO,
    _FCF_RATIO,
    _ASSETS_RATIO,
    _TEMPLATE_EQUIP_RATIO,
    _TEMPLATE_INFRA_RATIO,
    build_operator_input,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _profile(**kwargs) -> OperatorProfileInput:
    defaults = dict(
        name="Test Operator AS",
        country="Norge",
        n_sites=3,
        total_biomass_tonnes=9_200.0,
        biomass_value_per_tonne=72_000.0,
        annual_revenue_nok=897_000_000.0,
        annual_premium_nok=19_500_000.0,
    )
    defaults.update(kwargs)
    return OperatorProfileInput(**defaults)


# ── TestRiskParameterScaling ──────────────────────────────────────────────────

class TestRiskParameterScaling:
    def test_template_input_produces_template_severity(self):
        """Operator with same exposure as template → severity == template value."""
        op, _ = build_operator_input(_profile())
        assert op.risk_params.mean_loss_severity == _TEMPLATE_SEVERITY

    def test_larger_operator_higher_severity(self):
        big = _profile(total_biomass_tonnes=18_400.0)   # 2× template
        small = _profile(total_biomass_tonnes=4_600.0)  # 0.5× template
        op_big, _ = build_operator_input(big)
        op_small, _ = build_operator_input(small)
        assert op_big.risk_params.mean_loss_severity > _TEMPLATE_SEVERITY
        assert op_small.risk_params.mean_loss_severity < _TEMPLATE_SEVERITY

    def test_severity_scales_linearly_with_exposure(self):
        """2× biomass → 2× mean_loss_severity (within rounding)."""
        base = _profile(total_biomass_tonnes=9_200.0)
        double = _profile(total_biomass_tonnes=18_400.0)
        op_base, _ = build_operator_input(base)
        op_double, _ = build_operator_input(double)
        ratio = op_double.risk_params.mean_loss_severity / op_base.risk_params.mean_loss_severity
        assert ratio == pytest.approx(2.0, rel=0.01)

    def test_events_scale_with_sqrt_sites(self):
        """6 sites → sqrt(6/3) × template_events = sqrt(2) × 2.8."""
        op, _ = build_operator_input(_profile(n_sites=6))
        expected = _TEMPLATE_EVENTS * math.sqrt(6 / _TEMPLATE_N_SITES)
        assert op.risk_params.expected_annual_events == pytest.approx(expected, rel=1e-3)

    def test_template_sites_produce_template_events(self):
        op, _ = build_operator_input(_profile(n_sites=3))
        assert op.risk_params.expected_annual_events == pytest.approx(_TEMPLATE_EVENTS, rel=1e-3)

    def test_cv_and_cat_params_unchanged(self):
        """CV, catastrophe_probability, and cat_multiplier must not be scaled."""
        op, _ = build_operator_input(_profile(total_biomass_tonnes=3_000.0))
        assert op.risk_params.cv_loss_severity == pytest.approx(0.75, rel=1e-6)
        assert op.risk_params.catastrophe_probability == pytest.approx(0.04, rel=1e-6)
        assert op.risk_params.catastrophe_loss_multiplier == pytest.approx(8.5, rel=1e-6)


# ── TestFinancialScaling ──────────────────────────────────────────────────────

class TestFinancialScaling:
    def test_revenue_set_from_profile(self):
        revenue = 500_000_000.0
        op, _ = build_operator_input(_profile(annual_revenue_nok=revenue))
        assert op.financials.annual_revenue == revenue

    def test_ebitda_derived_from_revenue(self):
        revenue = 500_000_000.0
        op, _ = build_operator_input(_profile(annual_revenue_nok=revenue))
        expected = round(revenue * _EBITDA_MARGIN)
        assert op.financials.ebitda == pytest.approx(expected, rel=1e-3)

    def test_equity_derived_from_revenue(self):
        revenue = 600_000_000.0
        op, _ = build_operator_input(_profile(annual_revenue_nok=revenue))
        expected = round(revenue * _EQUITY_RATIO)
        assert op.financials.net_equity == pytest.approx(expected, rel=1e-3)

    def test_fcf_derived_from_revenue(self):
        revenue = 400_000_000.0
        op, _ = build_operator_input(_profile(annual_revenue_nok=revenue))
        expected = round(revenue * _FCF_RATIO)
        assert op.financials.free_cash_flow == pytest.approx(expected, rel=1e-3)

    def test_assets_derived_from_revenue(self):
        revenue = 700_000_000.0
        op, _ = build_operator_input(_profile(annual_revenue_nok=revenue))
        expected = round(revenue * _ASSETS_RATIO)
        assert op.financials.total_assets == pytest.approx(expected, rel=1e-3)


# ── TestEquipmentAllocation ───────────────────────────────────────────────────

class TestEquipmentAllocation:
    def test_total_equipment_scales_with_exposure(self):
        """Sum of equipment across all sites == user_exposure × equip_ratio (approx)."""
        p = _profile(total_biomass_tonnes=5_000.0, biomass_value_per_tonne=60_000.0)
        op, alloc = build_operator_input(p)
        user_exposure = 5_000.0 * 60_000.0
        expected_total_equip = user_exposure * _TEMPLATE_EQUIP_RATIO
        actual_total_equip = sum(s.equipment_value for s in op.sites)
        assert actual_total_equip == pytest.approx(expected_total_equip, rel=0.01)

    def test_total_infra_scales_with_exposure(self):
        p = _profile(total_biomass_tonnes=5_000.0, biomass_value_per_tonne=60_000.0)
        op, _ = build_operator_input(p)
        user_exposure = 5_000.0 * 60_000.0
        expected_total_infra = user_exposure * _TEMPLATE_INFRA_RATIO
        actual_total_infra = sum(s.infrastructure_value for s in op.sites)
        assert actual_total_infra == pytest.approx(expected_total_infra, rel=0.01)

    def test_equipment_does_not_inflate_with_extra_sites(self):
        """Equipment total must not grow when n_sites increases with same biomass."""
        p3 = _profile(n_sites=3, total_biomass_tonnes=9_200.0)
        p6 = _profile(n_sites=6, total_biomass_tonnes=9_200.0)
        op3, _ = build_operator_input(p3)
        op6, _ = build_operator_input(p6)
        equip3 = sum(s.equipment_value for s in op3.sites)
        equip6 = sum(s.equipment_value for s in op6.sites)
        # Both have the same biomass exposure, so totals should be approximately equal
        assert equip6 == pytest.approx(equip3, rel=0.05)


# ── TestBiomassAndRevenueConsistency ─────────────────────────────────────────

class TestBiomassAndRevenueConsistency:
    def test_site_biomass_sums_to_total(self):
        p = _profile(total_biomass_tonnes=8_000.0)
        op, _ = build_operator_input(p)
        assert sum(s.biomass_tonnes for s in op.sites) == pytest.approx(8_000.0, abs=60)

    def test_site_revenue_sums_to_total(self):
        revenue = 750_000_000.0
        op, _ = build_operator_input(_profile(annual_revenue_nok=revenue))
        assert sum(s.annual_revenue for s in op.sites) == pytest.approx(revenue, rel=0.01)

    def test_biomass_value_set_uniformly(self):
        value = 65_000.0
        op, _ = build_operator_input(_profile(biomass_value_per_tonne=value))
        for s in op.sites:
            assert s.biomass_value_per_tonne == value


# ── TestAllocationSummary ─────────────────────────────────────────────────────

class TestAllocationSummary:
    def test_tiv_ratio_correct(self):
        p = _profile(total_biomass_tonnes=9_200.0, biomass_value_per_tonne=72_000.0)
        _, alloc = build_operator_input(p)
        assert alloc.tiv_ratio == pytest.approx(1.0, rel=1e-4)

    def test_site_rows_count_matches_n_sites(self):
        for n in [1, 2, 3, 5]:
            _, alloc = build_operator_input(_profile(n_sites=n))
            assert len(alloc.sites) == n

    def test_site_weight_pct_sums_to_100(self):
        _, alloc = build_operator_input(_profile(n_sites=3))
        total_weight = sum(r.weight_pct for r in alloc.sites)
        assert total_weight == pytest.approx(100.0, abs=1.0)

    def test_financial_ratios_keys_present(self):
        _, alloc = build_operator_input(_profile())
        for key in ("ebitda_margin", "equity_ratio", "fcf_ratio", "assets_ratio"):
            assert key in alloc.financial_ratios

    def test_warnings_list_exists(self):
        _, alloc = build_operator_input(_profile())
        assert isinstance(alloc.warnings, list)

    def test_high_premium_ratio_triggers_warning(self):
        """Premium > 5 % of revenue should produce a warning."""
        _, alloc = build_operator_input(
            _profile(annual_premium_nok=60_000_000.0, annual_revenue_nok=500_000_000.0)
        )
        assert any("premium" in w.lower() or "Premium" in w for w in alloc.warnings)


# ── TestMCDifferentiation ─────────────────────────────────────────────────────

class TestMCDifferentiation:
    """Monte Carlo engine should produce meaningfully different E[loss] for
    operators of different size (validates that risk params actually scale)."""

    def _run_mc(self, profile, n=500):
        from models.monte_carlo import MonteCarloEngine
        op, _ = build_operator_input(profile)
        sim = MonteCarloEngine(op, n_simulations=n).run()
        return sim.mean_annual_loss

    def test_larger_operator_higher_expected_loss(self):
        small = _profile(total_biomass_tonnes=4_600.0)
        large = _profile(total_biomass_tonnes=18_400.0)
        loss_small = self._run_mc(small)
        loss_large = self._run_mc(large)
        assert loss_large > loss_small * 1.5

    def test_expected_loss_scales_approximately_linearly(self):
        """4× biomass → ~4× expected loss (Poisson × severity, both scale)."""
        base = _profile(total_biomass_tonnes=4_600.0)
        quad = _profile(total_biomass_tonnes=18_400.0)
        loss_base = self._run_mc(base, n=1_000)
        loss_quad = self._run_mc(quad, n=1_000)
        ratio = loss_quad / loss_base
        # Allow generous tolerance since events also scale (sqrt) + MC noise
        assert 2.0 < ratio < 6.0


# ── TestSiteCloning ───────────────────────────────────────────────────────────

class TestSiteCloning:
    def test_n_sites_1_returns_1_site(self):
        op, _ = build_operator_input(_profile(n_sites=1))
        assert len(op.sites) == 1

    def test_n_sites_2_returns_2_sites(self):
        op, _ = build_operator_input(_profile(n_sites=2))
        assert len(op.sites) == 2

    def test_n_sites_3_returns_3_sites(self):
        op, _ = build_operator_input(_profile(n_sites=3))
        assert len(op.sites) == 3

    def test_n_sites_5_returns_5_sites(self):
        op, _ = build_operator_input(_profile(n_sites=5))
        assert len(op.sites) == 5

    def test_generated_sites_not_called_prosessering(self):
        """When cloning, generated sites must not be named after the processing facility."""
        op, _ = build_operator_input(_profile(n_sites=6))
        extra_names = [s.name for s in op.sites[3:]]  # sites beyond the 3 template sites
        for name in extra_names:
            assert "Prosessering" not in name

    def test_generated_sites_have_production_type(self):
        """Generated farm sites must have site_type == 'production'."""
        op, _ = build_operator_input(_profile(n_sites=5))
        extra_sites = op.sites[3:]
        for s in extra_sites:
            assert s.site_type == "production"

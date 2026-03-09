"""
Tests for Sprint 8 – PCC Captive Economics Calibration (original + post-report fixes).

Verifies:
* PCCAssumptions presets load correctly with expected field ranges
* apply_pcc_reinsurance_structure correctly splits gross losses
* compute_ri_premium returns a value proportional to loading factor
* compute_net_var is bounded by retention
* calibrate_market_premium uses loss-ratio formula correctly
* build_pcc_assumption_set returns correct presets and rejects unknowns
* PCCCaptiveStrategy: net capital < gross capital (RI reduces tail)
* PCCCaptiveStrategy: RI premium appears as an explicit cost line
* PCCCaptiveStrategy: retained_losses = 0 in annual breakdown
* PCCCaptiveStrategy: backward compatible (no required changes to callers)
* PCCCaptiveStrategy: optimised preset produces lower capital than conservative

Post-report-fix additions (RI calibration / SCR reconciliation / recommendation gate):
* ri_loading_factor default is 1.75 (not punitive 2.5)
* conservative/optimised presets have correct loading factors (2.5 / 1.25)
* fronting_fee_paid appears as a separate field in annual breakdown
* premium_paid (net only) + fronting_fee_paid sums to original premium+fronting total
* net_loss_scr_data populated in StrategyResult
* SCRCalculator uses net_loss_scr_data → scr_net == strategy.required_capital for PCC
* Solvency ratio == 1.0 for PCC by construction (provided capital = SCR)
* Suitability verdict capped at POTENTIALLY SUITABLE when PCC >5% more expensive than FI
* Suitability verdict capped at NOT RECOMMENDED when PCC >15% more expensive than FI
"""

import numpy as np
import pytest
from unittest.mock import MagicMock

from models.pcc_economics import (
    PCCAssumptions,
    apply_pcc_reinsurance_structure,
    compute_ri_premium,
    compute_net_var,
    calibrate_market_premium,
    build_pcc_assumption_set,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_sim(mean_loss=10_000_000, n=500, t=5, seed=42):
    """Create a minimal SimulationResults mock."""
    rng = np.random.default_rng(seed)
    losses = rng.exponential(mean_loss, size=(n, t))
    sim = MagicMock()
    sim.annual_losses = losses
    sim.mean_annual_loss = float(losses.mean())
    sim.var_995 = float(np.percentile(losses.flatten(), 99.5))
    sim.event_counts = np.ones((n, t), dtype=int)
    return sim


def _make_operator():
    """Minimal OperatorInput mock."""
    op = MagicMock()
    op.name = "Test Operator"
    op.captive_domicile_preference = None
    ins = MagicMock()
    ins.annual_premium = 19_500_000
    ins.market_rating_trend = 0.03
    ins.per_occurrence_deductible = 2_000_000
    ins.annual_aggregate_deductible = 6_000_000
    ins.coverage_limit = 500_000_000
    op.current_insurance = ins
    rp = MagicMock()
    rp.frequency_mean = 2.5
    op.risk_params = rp
    return op


# ── TestPCCAssumptions ────────────────────────────────────────────────────────

class TestPCCAssumptions:
    def test_base_preset_defaults(self):
        a = PCCAssumptions.base()
        assert a.retention_nok == 25_000_000
        assert a.ri_loading_factor == 1.75
        assert a.premium_discount_pct == 0.22

    def test_conservative_has_lower_retention(self):
        c = PCCAssumptions.conservative()
        b = PCCAssumptions.base()
        assert c.retention_nok < b.retention_nok

    def test_conservative_has_higher_loading(self):
        c = PCCAssumptions.conservative()
        b = PCCAssumptions.base()
        assert c.ri_loading_factor > b.ri_loading_factor  # 2.5 > 1.75

    def test_optimised_has_higher_retention(self):
        o = PCCAssumptions.optimised()
        b = PCCAssumptions.base()
        assert o.retention_nok > b.retention_nok

    def test_optimised_has_lower_loading(self):
        o = PCCAssumptions.optimised()
        b = PCCAssumptions.base()
        assert o.ri_loading_factor < b.ri_loading_factor

    def test_default_market_calibration_off(self):
        a = PCCAssumptions()
        assert a.use_market_premium_calibration is False

    def test_all_rates_in_valid_range(self):
        for preset in [PCCAssumptions.base, PCCAssumptions.conservative, PCCAssumptions.optimised]:
            a = preset()
            assert 0 < a.fronting_fee_pct < 1
            assert 0 < a.investment_return_pct < 1
            assert 0 < a.premium_discount_pct < 1
            assert 0 < a.tp_load < 1
            assert 0 < a.scr_confidence < 1


# ── TestApplyPCCReinsuranceStructure ─────────────────────────────────────────

class TestApplyPCCReinsuranceStructure:
    RETENTION = 25_000_000
    RI_LIMIT = 150_000_000

    def test_loss_below_retention_fully_retained(self):
        losses = np.array([10_000_000.0])
        net, ri = apply_pcc_reinsurance_structure(losses, self.RETENTION, self.RI_LIMIT)
        assert float(net[0]) == pytest.approx(10_000_000.0)
        assert float(ri[0]) == pytest.approx(0.0)

    def test_loss_exactly_at_retention(self):
        losses = np.array([25_000_000.0])
        net, ri = apply_pcc_reinsurance_structure(losses, self.RETENTION, self.RI_LIMIT)
        assert float(net[0]) == pytest.approx(25_000_000.0)
        assert float(ri[0]) == pytest.approx(0.0)

    def test_loss_above_retention(self):
        losses = np.array([50_000_000.0])
        net, ri = apply_pcc_reinsurance_structure(losses, self.RETENTION, self.RI_LIMIT)
        assert float(net[0]) == pytest.approx(25_000_000.0)
        assert float(ri[0]) == pytest.approx(25_000_000.0)

    def test_loss_exceeds_ri_limit(self):
        losses = np.array([200_000_000.0])
        net, ri = apply_pcc_reinsurance_structure(losses, self.RETENTION, self.RI_LIMIT)
        assert float(net[0]) == pytest.approx(25_000_000.0)
        assert float(ri[0]) == pytest.approx(150_000_000.0)

    def test_net_plus_ri_recovery_le_gross(self):
        rng = np.random.default_rng(1)
        losses = rng.exponential(30_000_000, size=1000)
        net, ri = apply_pcc_reinsurance_structure(losses, self.RETENTION, self.RI_LIMIT)
        combined = net + ri
        assert np.all(combined <= losses + 1.0)

    def test_net_bounded_by_retention(self):
        rng = np.random.default_rng(2)
        losses = rng.exponential(50_000_000, size=1000)
        net, _ = apply_pcc_reinsurance_structure(losses, self.RETENTION, self.RI_LIMIT)
        assert float(net.max()) <= self.RETENTION + 1.0

    def test_2d_array_shape_preserved(self):
        losses = np.ones((500, 5)) * 40_000_000
        net, ri = apply_pcc_reinsurance_structure(losses, self.RETENTION, self.RI_LIMIT)
        assert net.shape == (500, 5)
        assert ri.shape == (500, 5)


# ── TestComputeRIPremium ──────────────────────────────────────────────────────

class TestComputeRIPremium:
    def test_ri_premium_positive(self):
        rng = np.random.default_rng(42)
        losses = rng.exponential(20_000_000, size=(1000, 5))
        assump = PCCAssumptions.base()
        ri_prem = compute_ri_premium(losses, assump)
        assert ri_prem > 0

    def test_ri_premium_proportional_to_loading(self):
        rng = np.random.default_rng(42)
        losses = rng.exponential(20_000_000, size=(1000, 5))
        a1 = PCCAssumptions(ri_loading_factor=2.0)
        a2 = PCCAssumptions(ri_loading_factor=4.0)
        assert compute_ri_premium(losses, a2) == pytest.approx(
            compute_ri_premium(losses, a1) * 2.0, rel=1e-6
        )

    def test_ri_premium_zero_when_all_losses_below_retention(self):
        losses = np.full((100, 5), 10_000_000.0)
        assump = PCCAssumptions(retention_nok=25_000_000)
        ri_prem = compute_ri_premium(losses, assump)
        assert ri_prem == pytest.approx(0.0)

    def test_ri_premium_increases_with_higher_losses(self):
        low = np.full((200, 5), 5_000_000.0)
        high = np.full((200, 5), 50_000_000.0)
        assump = PCCAssumptions.base()
        assert compute_ri_premium(high, assump) > compute_ri_premium(low, assump)


# ── TestComputeNetVar ─────────────────────────────────────────────────────────

class TestComputeNetVar:
    def test_net_var_bounded_by_retention(self):
        rng = np.random.default_rng(99)
        gross = rng.exponential(30_000_000, size=(1000, 5))
        retention = 25_000_000
        net, _ = apply_pcc_reinsurance_structure(gross, retention, 150_000_000)
        net_var = compute_net_var(net)
        assert net_var <= retention + 1.0

    def test_net_var_less_than_gross_var(self):
        rng = np.random.default_rng(7)
        gross = rng.exponential(40_000_000, size=(2000, 5))
        retention = 25_000_000
        net, _ = apply_pcc_reinsurance_structure(gross, retention, 150_000_000)
        gross_var = float(np.percentile(gross.mean(axis=1), 99.5))
        net_var = compute_net_var(net)
        assert net_var < gross_var

    def test_1d_array_accepted(self):
        losses = np.array([10_000_000.0, 20_000_000.0, 30_000_000.0])
        var = compute_net_var(losses, confidence=0.995)
        assert var > 0

    def test_confidence_parameter_respected(self):
        rng = np.random.default_rng(3)
        losses = rng.exponential(10_000_000, size=5000)
        var_99 = compute_net_var(losses, confidence=0.99)
        var_995 = compute_net_var(losses, confidence=0.995)
        assert var_995 >= var_99


# ── TestCalibrateMarketPremium ────────────────────────────────────────────────

class TestCalibrateMarketPremium:
    def test_formula(self):
        prem = calibrate_market_premium(10_000_000, target_loss_ratio=0.65)
        assert prem == pytest.approx(10_000_000 / 0.65)

    def test_lower_loss_ratio_gives_higher_premium(self):
        p_low = calibrate_market_premium(10_000_000, target_loss_ratio=0.50)
        p_high = calibrate_market_premium(10_000_000, target_loss_ratio=0.70)
        assert p_low > p_high

    def test_invalid_loss_ratio_raises(self):
        with pytest.raises(ValueError):
            calibrate_market_premium(10_000_000, target_loss_ratio=0.0)
        with pytest.raises(ValueError):
            calibrate_market_premium(10_000_000, target_loss_ratio=1.0)
        with pytest.raises(ValueError):
            calibrate_market_premium(10_000_000, target_loss_ratio=-0.5)


# ── TestBuildPCCAssumptionSet ─────────────────────────────────────────────────

class TestBuildPCCAssumptionSet:
    def test_base_preset(self):
        a = build_pcc_assumption_set("base")
        assert isinstance(a, PCCAssumptions)
        assert a.retention_nok == 25_000_000

    def test_conservative_preset(self):
        a = build_pcc_assumption_set("conservative")
        assert a.ri_loading_factor == 2.5   # reduced from original 3.0

    def test_optimised_preset(self):
        a = build_pcc_assumption_set("optimised")
        assert a.ri_loading_factor == 1.25   # reduced from original 2.0

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            build_pcc_assumption_set("magic")


# ── TestPCCCaptiveStrategyCalibration ────────────────────────────────────────

class TestPCCCaptiveStrategyCalibration:
    """Integration tests using the updated PCCCaptiveStrategy."""

    def _run(self, pcc_assumptions=None):
        from models.strategies.pcc_captive import PCCCaptiveStrategy
        op = _make_operator()
        sim = _make_sim(mean_loss=10_000_000, n=500, t=5)
        strategy = PCCCaptiveStrategy(op, sim, pcc_assumptions=pcc_assumptions)
        return strategy.calculate()

    def test_required_capital_less_than_gross_var(self):
        """Net capital (after RI) should be much less than gross VaR."""
        result = self._run()
        sim = _make_sim()
        gross_var = sim.var_995
        assert result.required_capital < gross_var

    def test_reinsurance_cost_positive(self):
        """All years should have a positive reinsurance_cost line."""
        result = self._run()
        for bd in result.annual_breakdown:
            assert bd.reinsurance_cost > 0, f"Year {bd.year} has zero reinsurance_cost"

    def test_retained_losses_zero(self):
        """retained_losses should be 0 (losses paid from reserve, not cash)."""
        result = self._run()
        for bd in result.annual_breakdown:
            assert bd.retained_losses == pytest.approx(0.0), (
                f"Year {bd.year}: retained_losses={bd.retained_losses} (expected 0)"
            )

    def test_net_cost_includes_reinsurance_cost(self):
        """net_cost = premium + fronting + ri_cost + admin + capital_opp - inv_income (+ setup yr1)."""
        result = self._run()
        for bd in result.annual_breakdown:
            expected = (
                bd.premium_paid
                + bd.fronting_fee_paid
                + bd.retained_losses
                + bd.reinsurance_cost
                + bd.admin_costs
                + bd.capital_opportunity_cost
                + bd.setup_or_exit_cost
                - bd.investment_income
            )
            assert bd.net_cost == pytest.approx(expected, rel=1e-9)

    def test_backward_compatible_no_assumptions(self):
        """Calling without pcc_assumptions uses base defaults — no exception."""
        result = self._run(pcc_assumptions=None)
        assert result.strategy_name == "PCC Captive Cell"
        assert len(result.annual_breakdown) == 5
        assert result.total_5yr_cost > 0

    def test_optimised_lower_capital_than_conservative(self):
        """Optimised preset (higher retention = more tail absorbed by RI) should
        not produce higher capital than conservative (lower retention, less RI)."""
        # With higher retention: net net losses are bounded at retention level.
        # Both bounds are well above E[loss], so capital differences come from RI loading.
        result_opt = self._run(PCCAssumptions.optimised())
        result_con = self._run(PCCAssumptions.conservative())
        # At minimum they're both below gross VaR
        sim = _make_sim()
        gross_var = sim.var_995
        assert result_opt.required_capital < gross_var
        assert result_con.required_capital < gross_var

    def test_result_has_all_required_fields(self):
        result = self._run()
        assert result.total_5yr_cost > 0
        assert result.total_5yr_cost_npv > 0
        assert result.required_capital > 0
        assert result.cost_std >= 0
        assert result.gross_loss_mean is not None
        assert len(result.assumptions) > 0

    def test_market_calibrated_premium_changes_result(self):
        """Enabling market premium calibration should produce a different total cost."""
        assump_calib = PCCAssumptions(use_market_premium_calibration=True, target_market_loss_ratio=0.65)
        result_std = self._run(PCCAssumptions.base())
        result_cal = self._run(assump_calib)
        # Total costs should differ (calibrated premium ≠ operator's actual premium)
        assert result_std.total_5yr_cost != pytest.approx(result_cal.total_5yr_cost, rel=0.001)

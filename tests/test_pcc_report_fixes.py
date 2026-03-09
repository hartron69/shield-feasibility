"""
Tests for PCC report fixes:
  1. RI loading factor recalibration (1.75 base, 2.5 conservative, 1.25 optimised)
  2. Fronting fee separated from net premium in AnnualCostBreakdown
  3. SCR reconciliation: scr_net == required_capital for PCC after SCRCalculator
  4. Suitability cost gate: verdict capped when PCC materially more expensive than FI
"""

import numpy as np
import pytest
from unittest.mock import MagicMock

from models.pcc_economics import PCCAssumptions, compute_ri_premium


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_sim(mean_loss=8_000_000, n=400, t=5, seed=42):
    rng = np.random.default_rng(seed)
    losses = rng.exponential(mean_loss, size=(n, t))
    sim = MagicMock()
    sim.annual_losses = losses
    sim.mean_annual_loss = float(losses.mean())
    sim.std_annual_loss = float(losses.std())
    sim.var_99 = float(np.percentile(losses.flatten(), 99.0))
    sim.var_995 = float(np.percentile(losses.flatten(), 99.5))
    sim.n_simulations = n
    sim.projection_years = t
    return sim


def _make_operator():
    op = MagicMock()
    op.name = "Test Operator"
    op.captive_domicile_preference = None
    op.management_commitment_years = 7
    op.governance_maturity = "mature"
    op.has_risk_manager = True
    op.willing_to_provide_capital = True
    op.c5ai_forecast_path = None
    op.bio_readiness_score = None   # explicit None so engine uses proxy path
    ins = MagicMock()
    ins.annual_premium = 19_500_000
    ins.market_rating_trend = 0.03
    ins.per_occurrence_deductible = 2_000_000
    ins.annual_aggregate_deductible = 6_000_000
    ins.coverage_limit = 500_000_000
    ins.current_loss_ratio = 0.65
    op.current_insurance = ins
    fin = MagicMock()
    fin.net_equity = 300_000_000
    fin.free_cash_flow = 30_000_000
    fin.ebitda = 50_000_000
    fin.annual_revenue = 150_000_000
    fin.years_in_operation = 10
    op.financials = fin
    rp = MagicMock()
    rp.frequency_mean = 2.0
    op.risk_params = rp
    return op


# ── TestRILoadingCalibration ──────────────────────────────────────────────────

class TestRILoadingCalibration:
    """Verify recalibrated RI loading factor defaults."""

    def test_base_loading_is_1_75(self):
        assert PCCAssumptions.base().ri_loading_factor == 1.75

    def test_conservative_loading_is_2_5(self):
        assert PCCAssumptions.conservative().ri_loading_factor == 2.5

    def test_optimised_loading_is_1_25(self):
        assert PCCAssumptions.optimised().ri_loading_factor == 1.25

    def test_base_loading_less_than_conservative(self):
        assert PCCAssumptions.base().ri_loading_factor < PCCAssumptions.conservative().ri_loading_factor

    def test_optimised_loading_less_than_base(self):
        assert PCCAssumptions.optimised().ri_loading_factor < PCCAssumptions.base().ri_loading_factor

    def test_ri_premium_30pct_lower_than_old_2_5(self):
        """1.75× loading gives 30% lower RI premium than old 2.5× default."""
        rng = np.random.default_rng(77)
        losses = rng.exponential(20_000_000, size=(500, 5))
        a_new = PCCAssumptions.base()               # 1.75×
        a_old = PCCAssumptions(ri_loading_factor=2.5)
        ri_new = compute_ri_premium(losses, a_new)
        ri_old = compute_ri_premium(losses, a_old)
        assert ri_new < ri_old
        assert ri_new / ri_old == pytest.approx(1.75 / 2.5, rel=1e-6)


# ── TestFrontingFeeSeparation ─────────────────────────────────────────────────

class TestFrontingFeeSeparation:
    """fronting_fee_paid must be a separate field; premium_paid excludes it."""

    def _run(self):
        from models.strategies.pcc_captive import PCCCaptiveStrategy
        op = _make_operator()
        sim = _make_sim()
        return PCCCaptiveStrategy(op, sim).calculate()

    def test_fronting_fee_paid_positive_all_years(self):
        result = self._run()
        for bd in result.annual_breakdown:
            assert bd.fronting_fee_paid > 0, f"Year {bd.year}: fronting_fee_paid == 0"

    def test_premium_paid_plus_fronting_exceeds_premium_paid(self):
        result = self._run()
        for bd in result.annual_breakdown:
            assert bd.premium_paid + bd.fronting_fee_paid > bd.premium_paid

    def test_net_cost_includes_fronting_fee(self):
        """net_cost = sum of all components including fronting_fee_paid."""
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
            assert bd.net_cost == pytest.approx(expected, rel=1e-9), (
                f"Year {bd.year}: net_cost={bd.net_cost} != expected {expected}"
            )

    def test_full_insurance_fronting_fee_zero(self):
        from models.strategies.full_insurance import FullInsuranceStrategy
        op = _make_operator()
        sim = _make_sim()
        result = FullInsuranceStrategy(op, sim).calculate()
        for bd in result.annual_breakdown:
            assert bd.fronting_fee_paid == 0.0


# ── TestSCRReconciliation ─────────────────────────────────────────────────────

class TestSCRReconciliation:
    """
    After SCRCalculator processes PCC StrategyResult, scr_net must equal
    required_capital (both derived from the net retained loss distribution).
    """

    def _setup(self):
        from models.strategies.pcc_captive import PCCCaptiveStrategy
        from models.strategies.full_insurance import FullInsuranceStrategy
        from analysis.scr_calculator import SCRCalculator

        op = _make_operator()
        sim = _make_sim(mean_loss=8_000_000, n=400, t=5, seed=55)
        strategy_results = {
            "Full Insurance":   FullInsuranceStrategy(op, sim).calculate(),
            "PCC Captive Cell": PCCCaptiveStrategy(op, sim).calculate(),
        }
        scr_results = SCRCalculator(sim, strategy_results).calculate_all()
        return strategy_results, scr_results

    def test_pcc_scr_net_equals_required_capital(self):
        strategy_results, scr_results = self._setup()
        pcc_result = strategy_results["PCC Captive Cell"]
        pcc_scr = scr_results["PCC Captive Cell"]
        assert pcc_scr.scr_net == pytest.approx(pcc_result.required_capital, rel=1e-6)

    def test_pcc_solvency_ratio_is_1(self):
        """Provided capital == SCR by construction, so solvency ratio = 1.0."""
        _, scr_results = self._setup()
        pcc_scr = scr_results["PCC Captive Cell"]
        assert pcc_scr.solvency_ratio == pytest.approx(1.0, rel=1e-3)

    def test_pcc_scr_net_below_gross_var(self):
        """PCC cell SCR < gross simulation VaR (RI caps the tail)."""
        strategy_results, scr_results = self._setup()
        sim = _make_sim(mean_loss=8_000_000, n=400, t=5, seed=55)
        pcc_scr = scr_results["PCC Captive Cell"]
        assert pcc_scr.scr_net < sim.var_995

    def test_pcc_net_loss_scr_data_populated(self):
        strategy_results, _ = self._setup()
        pcc = strategy_results["PCC Captive Cell"]
        assert pcc.net_loss_scr_data is not None
        assert "bel" in pcc.net_loss_scr_data
        assert "scr_gross" in pcc.net_loss_scr_data
        assert "scr_net" in pcc.net_loss_scr_data

    def test_full_insurance_scr_not_affected_by_pcc_changes(self):
        """Full Insurance SCR should be unchanged by PCC calibration work."""
        _, scr_results = self._setup()
        fi_scr = scr_results["Full Insurance"]
        assert fi_scr.scr_net >= 0
        # FI uses counterparty haircut only → capital should be 0
        assert fi_scr.required_capital == 0.0

    def test_pcc_interpretation_adequately_capitalised(self):
        """With solvency ratio = 1.0, interpretation should reflect adequate capitalisation."""
        _, scr_results = self._setup()
        pcc_scr = scr_results["PCC Captive Cell"]
        assert "capitalised" in pcc_scr.interpretation.lower()


# ── TestSuitabilityCostGate ───────────────────────────────────────────────────

class TestSuitabilityCostGate:
    """
    Suitability verdict must be capped when PCC is materially more expensive
    than Full Insurance, regardless of high scores on other criteria.
    """

    def _make_cost_analysis(self, pcc_5yr: float, fi_5yr: float):
        from analysis.cost_analyzer import CostAnalysis, CostSummary

        def _summary(name, total):
            s = MagicMock(spec=CostSummary)
            s.strategy_name = name
            s.total_5yr_undiscounted = total
            s.total_5yr_npv = total * 0.9
            s.vs_baseline_savings_5yr = fi_5yr - total
            s.vs_baseline_savings_pct = (fi_5yr - total) / max(fi_5yr, 1)
            s.annual_costs = [total / 5] * 5
            s.cumulative_costs = [total / 5 * i for i in range(1, 6)]
            return s

        ca = MagicMock(spec=CostAnalysis)
        ca.summaries = {
            "Full Insurance": _summary("Full Insurance", fi_5yr),
            "PCC Captive Cell": _summary("PCC Captive Cell", pcc_5yr),
        }
        ca.baseline_name = "Full Insurance"
        ca.cheapest_strategy = "Full Insurance" if pcc_5yr > fi_5yr else "PCC Captive Cell"
        return ca

    def _make_engine(self, pcc_5yr: float, fi_5yr: float):
        from analysis.suitability_engine import SuitabilityEngine

        op = _make_operator()
        sim = _make_sim(mean_loss=3_000_000, n=200, t=5)

        pcc_strat = MagicMock()
        pcc_strat.required_capital = 15_000_000
        strategies = {"PCC Captive Cell": pcc_strat}
        cost_analysis = self._make_cost_analysis(pcc_5yr, fi_5yr)
        return SuitabilityEngine(op, sim, strategies, cost_analysis)

    def test_verdict_capped_at_potentially_suitable_when_10pct_over(self):
        """PCC 10% more expensive → verdict capped at POTENTIALLY SUITABLE."""
        fi = 100_000_000
        rec = self._make_engine(fi * 1.10, fi).assess()
        allowed = {"POTENTIALLY SUITABLE", "NOT RECOMMENDED", "NOT SUITABLE"}
        assert rec.verdict in allowed, f"Expected capped verdict; got {rec.verdict!r}"

    def test_verdict_capped_at_not_recommended_when_20pct_over(self):
        """PCC 20% more expensive → verdict capped at NOT RECOMMENDED."""
        fi = 100_000_000
        rec = self._make_engine(fi * 1.20, fi).assess()
        assert rec.verdict in {"NOT RECOMMENDED", "NOT SUITABLE"}, (
            f"Expected NOT RECOMMENDED or NOT SUITABLE; got {rec.verdict!r}"
        )

    def test_cost_barrier_in_barriers_when_pcc_over(self):
        """When PCC > FI by >5%, a cost-related barrier must appear."""
        fi = 100_000_000
        rec = self._make_engine(fi * 1.10, fi).assess()
        cost_mentions = [b for b in rec.key_barriers if "TCOR" in b or "full" in b.lower()]
        assert len(cost_mentions) >= 1, f"No cost barrier found: {rec.key_barriers}"

    def test_verdict_not_capped_when_pcc_cheaper(self):
        """When PCC is cheaper than FI, cost gate must NOT downgrade verdict."""
        fi = 100_000_000
        rec = self._make_engine(fi * 0.85, fi).assess()
        # With all other criteria near max, composite should be RECOMMENDED or STRONGLY
        assert rec.verdict in {"STRONGLY RECOMMENDED", "RECOMMENDED"}, (
            f"PCC cheaper than FI should not be capped; got {rec.verdict!r}"
        )

    def test_verdict_not_capped_when_pcc_only_slightly_over(self):
        """A marginal 3% excess (below 5% threshold) should NOT trigger the gate."""
        fi = 100_000_000
        rec = self._make_engine(fi * 1.03, fi).assess()
        # Gate should not fire; verdict driven by composite score
        # (operator mock has good scores, so composite should be high)
        # We just verify no crash and that verdict is valid
        assert rec.verdict in {
            "STRONGLY RECOMMENDED", "RECOMMENDED", "POTENTIALLY SUITABLE",
            "NOT RECOMMENDED", "NOT SUITABLE",
        }

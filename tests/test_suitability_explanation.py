"""
Tests for SuitabilityExplanation and SuitabilityPath (AP5).
"""
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from analysis.suitability_engine import (
    SuitabilityEngine,
    SuitabilityExplanation,
    SuitabilityPath,
    CriterionScore,
)


def _make_mock_operator(
    premium=15_000_000,
    management_years=5,
    has_risk_manager=True,
    governance="developing",
    willing_capital=True,
    bio_score=None,
):
    op = MagicMock()
    op.name = "TestOp AS"
    op.current_insurance.annual_premium = premium
    op.current_insurance.market_rating_trend = 0.03
    op.current_insurance.current_loss_ratio = 0.45
    op.management_commitment_years = management_years
    op.has_risk_manager = has_risk_manager
    op.governance_maturity = governance
    op.willing_to_provide_capital = willing_capital
    op.bio_readiness_score = bio_score
    op.captive_domicile_preference = "Guernsey"
    op.financials.net_equity = 200_000_000
    op.financials.free_cash_flow = 30_000_000
    op.financials.annual_revenue = 500_000_000
    op.financials.ebitda = 100_000_000
    op.financials.years_in_operation = 8
    op.c5ai_forecast_path = None
    return op


def _make_mock_sim():
    rng = np.random.default_rng(42)
    losses = rng.exponential(10_000_000, size=(1000, 5))
    sim = MagicMock()
    sim.annual_losses = losses
    sim.mean_annual_loss = float(losses.mean())
    sim.std_annual_loss = float(losses.std())
    sim.median_annual_loss = float(np.median(losses))
    sim.var_90 = float(np.percentile(losses, 90))
    sim.var_95 = float(np.percentile(losses, 95))
    sim.var_99 = float(np.percentile(losses, 99))
    sim.var_995 = float(np.percentile(losses, 99.5))
    sim.tvar_95 = float(losses.flatten()[losses.flatten() >= sim.var_95].mean())
    sim.n_simulations = 1000
    sim.projection_years = 5
    sim.c5ai_enriched = False
    return sim


def _make_mock_strategy_results(sim):
    pcc = MagicMock()
    pcc.required_capital = 30_000_000
    return {"PCC Captive Cell": pcc}


def _make_mock_cost_analysis(savings_pct=0.15, savings_5yr=15_000_000, total=100_000_000):
    cost = MagicMock()
    cost.summaries = {
        "Full Insurance": MagicMock(total_5yr_undiscounted=total),
        "PCC Captive Cell": MagicMock(
            vs_baseline_savings_pct=savings_pct,
            vs_baseline_savings_5yr=savings_5yr,
        ),
    }
    return cost


class TestSuitabilityExplanation:
    def test_fields_present(self):
        expl = SuitabilityExplanation(
            criterion_name="Test",
            score=45.0,
            gap_to_good=20.0,
            improvement_actions=["Do something"],
            priority="important",
            timeline="6-12 months",
            impact_on_score=3.6,
        )
        assert expl.criterion_name == "Test"
        assert expl.gap_to_good == 20.0
        assert expl.priority == "important"

    def test_zero_gap_for_good_score(self):
        expl = SuitabilityExplanation(
            criterion_name="Test",
            score=75.0,
            gap_to_good=0.0,
            improvement_actions=[],
            priority="nice-to-have",
            timeline="1-3 years",
            impact_on_score=0.0,
        )
        assert expl.gap_to_good == 0.0


class TestSuitabilityPath:
    def test_fields_present(self):
        path = SuitabilityPath(
            current_verdict="POTENTIALLY SUITABLE",
            target_verdict="RECOMMENDED",
            total_gap=10.0,
            prioritized_actions=[],
            estimated_months_to_target=12,
            board_narrative="Test narrative.",
        )
        assert path.current_verdict == "POTENTIALLY SUITABLE"
        assert path.estimated_months_to_target == 12


class TestSuitabilityEngineExplain:
    def _make_engine(self, **kwargs):
        op = _make_mock_operator(**kwargs)
        sim = _make_mock_sim()
        strategies = _make_mock_strategy_results(sim)
        cost = _make_mock_cost_analysis()
        return SuitabilityEngine(op, sim, strategies, cost)

    def test_explain_returns_suitability_path(self):
        engine = self._make_engine()
        path = engine.explain()
        assert isinstance(path, SuitabilityPath)

    def test_explain_has_prioritized_actions(self):
        engine = self._make_engine()
        path = engine.explain()
        assert len(path.prioritized_actions) > 0
        for action in path.prioritized_actions:
            assert isinstance(action, SuitabilityExplanation)

    def test_actions_sorted_by_impact(self):
        engine = self._make_engine()
        path = engine.explain()
        impacts = [a.impact_on_score for a in path.prioritized_actions]
        assert impacts == sorted(impacts, reverse=True)

    def test_all_criteria_have_explanations(self):
        engine = self._make_engine()
        path = engine.explain()
        # Should have one explanation per criterion (6 total)
        assert len(path.prioritized_actions) == 6

    def test_critical_criteria_have_actions(self):
        # Low premium → "Premium Volume" should be critical
        engine = self._make_engine(premium=500_000)
        path = engine.explain()
        vol_expl = next(
            (a for a in path.prioritized_actions if a.criterion_name == "Premium Volume"),
            None
        )
        assert vol_expl is not None
        assert vol_expl.priority == "critical"
        assert len(vol_expl.improvement_actions) > 0

    def test_board_narrative_non_empty(self):
        engine = self._make_engine()
        path = engine.explain()
        assert len(path.board_narrative) > 50

    def test_total_gap_non_negative(self):
        engine = self._make_engine()
        path = engine.explain()
        assert path.total_gap >= 0.0

    def test_target_verdict_is_higher(self):
        engine = self._make_engine()
        path = engine.explain()
        verdict_order = [
            "NOT SUITABLE", "NOT RECOMMENDED",
            "POTENTIALLY SUITABLE", "RECOMMENDED", "STRONGLY RECOMMENDED"
        ]
        current_idx = next(
            (i for i, v in enumerate(verdict_order) if v in path.current_verdict), 0
        )
        target_idx = next(
            (i for i, v in enumerate(verdict_order) if v in path.target_verdict), 0
        )
        assert target_idx >= current_idx

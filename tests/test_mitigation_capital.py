"""
Tests for Sprint 3 – Mitigation-to-Capital Impact.

Verifies that MitigationCapitalAnalyzer correctly computes:
  - expected loss, SCR, TCOR deltas
  - retained / reinsured / net-captive decomposition (with and without CaptiveStructure)
  - ranking helpers (rank_by_tcor_impact, rank_by_scr_impact, rank_by_suitability_impact)
  - suitability linkage estimates
  - build_mitigation_impact_summary() factory
  - MitigationScenario.mitigated_annual_losses field (Sprint 3 prerequisite)
  - Report model new classes and PlatformReport extension
"""

import numpy as np
import pytest
from unittest.mock import MagicMock

from analysis.mitigation import (
    MitigationAction,
    MitigationAnalyzer,
    MitigationCapitalImpact,
    MitigationCapitalAnalyzer,
    PREDEFINED_MITIGATIONS,
    build_mitigation_impact_summary,
)
from models.captive_structure import (
    CaptiveStructure,
    RetentionLayer,
    ReinsuranceLayer,
)
from reporting.report_model import (
    CapitalEfficiencySummary,
    MitigationImpactSummary,
    PlatformReport,
    ExecutiveSummary,
    RiskMetricsSummary,
    InsuranceStructureComparison,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_sim(n=500, t=5, seed=42, mean_loss=10_000_000):
    rng = np.random.default_rng(seed)
    losses = rng.exponential(mean_loss, size=(n, t))
    sim = MagicMock()
    sim.annual_losses = losses
    sim.mean_annual_loss = float(losses.mean())
    sim.var_995 = float(np.percentile(losses.flatten(), 99.5))
    return sim


def _make_captive(per_occ=2_000_000, limit=20_000_000):
    return CaptiveStructure(
        operator_name="Test Operator",
        retention=RetentionLayer(
            name="Deductible",
            per_occurrence_retention=per_occ,
            annual_aggregate_retention=per_occ * 3,
        ),
        captive_layer=ReinsuranceLayer(
            name="Captive Layer",
            attachment_point=per_occ,
            limit=limit - per_occ,
            participation_pct=100.0,
            estimated_premium=500_000,
        ),
    )


def _make_bio_bd(sim, fractions=None):
    if fractions is None:
        fractions = {"hab": 0.4, "lice": 0.3, "jellyfish": 0.2, "pathogen": 0.1}
    return {rt: sim.annual_losses * f for rt, f in fractions.items()}


# ── MitigationScenario.mitigated_annual_losses ────────────────────────────────

class TestMitigatedAnnualLossesField:
    def test_populated_after_compare(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        scenario = analyzer.compare([action])
        assert scenario.mitigated_annual_losses is not None

    def test_shape_matches_sim(self):
        sim = _make_sim(n=200, t=3)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        scenario = analyzer.compare([action])
        assert scenario.mitigated_annual_losses.shape == (200, 3)

    def test_empty_actions_returns_baseline_array(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        scenario = analyzer.compare([])
        np.testing.assert_array_equal(
            scenario.mitigated_annual_losses, sim.annual_losses
        )

    def test_values_less_than_baseline(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        scenario = analyzer.compare([action])
        assert scenario.mitigated_annual_losses.mean() < sim.annual_losses.mean()

    def test_populated_in_uncertainty_mode(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        rng = np.random.default_rng(0)
        scenario = analyzer.compare([action], use_uncertainty=True, rng=rng)
        assert scenario.mitigated_annual_losses is not None


# ── MitigationCapitalAnalyzer – no CaptiveStructure ──────────────────────────

class TestCapitalAnalyzerNoCaptive:
    def test_returns_impact(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        impact = ca.analyze([action])
        assert isinstance(impact, MitigationCapitalImpact)

    def test_baseline_matches_sim(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        impact = ca.analyze([action])
        assert abs(impact.baseline_expected_loss - sim.mean_annual_loss) < 1.0
        assert abs(impact.baseline_scr - sim.var_995) < 1.0

    def test_mitigated_loss_lower(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        impact = ca.analyze([action])
        assert impact.mitigated_expected_loss < impact.baseline_expected_loss

    def test_delta_expected_loss_negative(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        impact = ca.analyze([action])
        assert impact.delta_expected_loss < 0

    def test_delta_scr_non_positive(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        impact = ca.analyze([action])
        assert impact.delta_scr <= 0

    def test_capital_release_positive(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        impact = ca.analyze([action])
        assert impact.capital_release >= 0

    def test_no_captive_retained_equals_mitigated_loss(self):
        """Without a captive structure, all losses are retained."""
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim, captive_structure=None)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        impact = ca.analyze([action])
        assert abs(impact.mitigated_retained_mean - impact.mitigated_expected_loss) < 1.0

    def test_no_captive_reinsured_zero(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim, captive_structure=None)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        impact = ca.analyze([action])
        assert impact.mitigated_reinsured_mean == pytest.approx(0.0)

    def test_tcor_includes_mitigation_cost(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        impact = ca.analyze([action])
        expected_mitigated_tcor = impact.mitigated_expected_loss + action.annual_cost_nok
        assert abs(impact.mitigated_tcor - expected_mitigated_tcor) < 1.0

    def test_baseline_tcor_equals_baseline_expected_loss(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        impact = ca.analyze([action])
        assert abs(impact.baseline_tcor - impact.baseline_expected_loss) < 1.0

    def test_suitability_delta_populated(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        impact = ca.analyze([action])
        assert impact.estimated_suitability_delta is not None

    def test_suitability_delta_positive(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        impact = ca.analyze([action])
        assert impact.estimated_suitability_delta >= 0.0

    def test_top_improved_criteria_populated(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        impact = ca.analyze([action])
        assert isinstance(impact.top_improved_criteria, list)
        assert len(impact.top_improved_criteria) > 0


# ── MitigationCapitalAnalyzer – with CaptiveStructure ────────────────────────

class TestCapitalAnalyzerWithCaptive:
    def test_returns_impact(self):
        sim = _make_sim()
        captive = _make_captive()
        ca = MitigationCapitalAnalyzer(sim, captive)
        impact = ca.analyze([PREDEFINED_MITIGATIONS["lice_barriers"]])
        assert isinstance(impact, MitigationCapitalImpact)

    def test_retained_less_than_baseline(self):
        sim = _make_sim()
        captive = _make_captive()
        ca = MitigationCapitalAnalyzer(sim, captive)
        impact = ca.analyze([PREDEFINED_MITIGATIONS["lice_barriers"]])
        assert impact.mitigated_retained_mean <= impact.baseline_retained_mean

    def test_reinsured_non_negative(self):
        sim = _make_sim()
        captive = _make_captive()
        ca = MitigationCapitalAnalyzer(sim, captive)
        impact = ca.analyze([PREDEFINED_MITIGATIONS["jellyfish_mitigation"]])
        assert impact.mitigated_reinsured_mean >= 0.0

    def test_net_captive_non_negative(self):
        sim = _make_sim()
        captive = _make_captive()
        ca = MitigationCapitalAnalyzer(sim, captive)
        impact = ca.analyze([PREDEFINED_MITIGATIONS["jellyfish_mitigation"]])
        assert impact.mitigated_net_captive_mean >= 0.0

    def test_baseline_retained_consistent(self):
        """Baseline retained should equal CaptiveStructure.compute_net_loss mean."""
        sim = _make_sim()
        captive = _make_captive()
        ca = MitigationCapitalAnalyzer(sim, captive)
        expected_retained = float(captive.compute_net_loss(sim.annual_losses).mean())
        impact = ca.analyze([PREDEFINED_MITIGATIONS["lice_barriers"]])
        assert abs(impact.baseline_retained_mean - expected_retained) < 1.0

    def test_delta_retained_negative(self):
        sim = _make_sim()
        captive = _make_captive()
        ca = MitigationCapitalAnalyzer(sim, captive)
        impact = ca.analyze([PREDEFINED_MITIGATIONS["jellyfish_mitigation"]])
        assert impact.delta_retained_mean <= 0

    def test_multiple_actions_more_capital_efficient(self):
        sim = _make_sim()
        captive = _make_captive()
        ca = MitigationCapitalAnalyzer(sim, captive)
        single = ca.analyze([PREDEFINED_MITIGATIONS["jellyfish_mitigation"]])
        bundle = ca.analyze(list(PREDEFINED_MITIGATIONS.values()))
        assert bundle.capital_release >= single.capital_release

    def test_bio_breakdown_integration(self):
        sim = _make_sim()
        captive = _make_captive()
        bio_bd = _make_bio_bd(sim)
        ca = MitigationCapitalAnalyzer(sim, captive)
        impact = ca.analyze(
            [PREDEFINED_MITIGATIONS["jellyfish_mitigation"]],
            bio_loss_breakdown=bio_bd,
        )
        assert impact.delta_expected_loss < 0


# ── analyze_all_predefined ────────────────────────────────────────────────────

class TestAnalyzeAllPredefined:
    def test_returns_correct_count(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        impacts = ca.analyze_all_predefined()
        # 7 individual + 1 bundle
        assert len(impacts) == len(PREDEFINED_MITIGATIONS) + 1

    def test_all_reduce_expected_loss(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        impacts = ca.analyze_all_predefined()
        for impact in impacts:
            assert impact.mitigated_expected_loss <= impact.baseline_expected_loss

    def test_bundle_has_most_capital_release(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        impacts = ca.analyze_all_predefined()
        bundle = next(i for i in impacts if i.scenario_name == "full_mitigation_bundle")
        singles = [i for i in impacts if i.scenario_name != "full_mitigation_bundle"]
        assert bundle.capital_release >= max(s.capital_release for s in singles)


# ── Ranking helpers ───────────────────────────────────────────────────────────

class TestRankingHelpers:
    def _get_impacts(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        return ca.analyze_all_predefined(), ca

    def test_rank_by_tcor_ascending(self):
        impacts, ca = self._get_impacts()
        ranked = ca.rank_by_tcor_impact(impacts)
        for i in range(len(ranked) - 1):
            assert ranked[i].delta_tcor <= ranked[i + 1].delta_tcor

    def test_rank_by_scr_ascending(self):
        impacts, ca = self._get_impacts()
        ranked = ca.rank_by_scr_impact(impacts)
        for i in range(len(ranked) - 1):
            assert ranked[i].delta_scr <= ranked[i + 1].delta_scr

    def test_rank_by_suitability_descending(self):
        impacts, ca = self._get_impacts()
        ranked = ca.rank_by_suitability_impact(impacts)
        for i in range(len(ranked) - 1):
            d1 = ranked[i].estimated_suitability_delta or 0.0
            d2 = ranked[i + 1].estimated_suitability_delta or 0.0
            assert d1 >= d2

    def test_rank_preserves_all_elements(self):
        impacts, ca = self._get_impacts()
        ranked = ca.rank_by_tcor_impact(impacts)
        assert len(ranked) == len(impacts)


# ── Uncertainty mode ──────────────────────────────────────────────────────────

class TestCapitalAnalyzerUncertaintyMode:
    def test_uncertainty_mode_returns_impact(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        rng = np.random.default_rng(3)
        impact = ca.analyze([action], use_uncertainty=True, rng=rng)
        assert isinstance(impact, MitigationCapitalImpact)

    def test_uncertainty_mode_reduces_loss(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        rng = np.random.default_rng(7)
        impact = ca.analyze([action], use_uncertainty=True, rng=rng)
        assert impact.mitigated_expected_loss < impact.baseline_expected_loss

    def test_auto_rng_when_none_in_uncertainty(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        impact = ca.analyze([action], use_uncertainty=True, rng=None)
        assert impact is not None


# ── build_mitigation_impact_summary ──────────────────────────────────────────

class TestBuildMitigationImpactSummary:
    def _get_impacts(self):
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        return ca.analyze_all_predefined()

    def test_returns_summary(self):
        impacts = self._get_impacts()
        summary = build_mitigation_impact_summary(impacts)
        assert isinstance(summary, MitigationImpactSummary)

    def test_baseline_fields_consistent(self):
        impacts = self._get_impacts()
        summary = build_mitigation_impact_summary(impacts)
        assert summary.baseline_expected_loss > 0
        assert summary.baseline_scr > 0

    def test_best_scenario_lower_tcor(self):
        impacts = self._get_impacts()
        summary = build_mitigation_impact_summary(impacts)
        assert summary.best_scenario_tcor <= summary.baseline_tcor

    def test_recommended_actions_populated(self):
        impacts = self._get_impacts()
        summary = build_mitigation_impact_summary(impacts)
        assert isinstance(summary.recommended_actions, list)
        assert len(summary.recommended_actions) >= 1

    def test_delta_scr_non_positive(self):
        impacts = self._get_impacts()
        summary = build_mitigation_impact_summary(impacts)
        assert summary.delta_scr <= 0

    def test_net_5yr_benefit(self):
        impacts = self._get_impacts()
        summary = build_mitigation_impact_summary(impacts, projection_years=5)
        # Net benefit = (baseline - mitigated - cost) * 5
        annual_saving = summary.baseline_expected_loss - summary.best_scenario_expected_loss
        expected_net = (annual_saving - summary.total_mitigation_cost_annual) * 5
        assert abs(summary.net_5yr_benefit - expected_net) < 1.0

    def test_raises_on_empty_list(self):
        with pytest.raises(ValueError):
            build_mitigation_impact_summary([])

    def test_custom_projection_years(self):
        impacts = self._get_impacts()
        s5 = build_mitigation_impact_summary(impacts, projection_years=5)
        s10 = build_mitigation_impact_summary(impacts, projection_years=10)
        # 10-yr benefit should be exactly double the 5-yr (linear)
        assert abs(s10.net_5yr_benefit - s5.net_5yr_benefit * 2) < 1.0


# ── Report model: new dataclasses ────────────────────────────────────────────

class TestReportModelNewClasses:
    def test_capital_efficiency_summary_creates(self):
        ces = CapitalEfficiencySummary(
            optimal_retention=5_000_000,
            minimum_tcor=20_000_000,
            current_tcor_estimate=25_000_000,
            potential_saving_nok=5_000_000,
            recommended_structure_description="XS 5M xs 5M",
        )
        assert ces.potential_saving_nok == pytest.approx(5_000_000)

    def test_mitigation_impact_summary_creates(self):
        mis = MitigationImpactSummary(
            baseline_expected_loss=20_000_000,
            best_scenario_expected_loss=15_000_000,
            best_scenario_name="lice_barriers",
            total_mitigation_cost_annual=800_000,
            net_5yr_benefit=21_000_000,
            recommended_actions=["lice_barriers"],
        )
        assert mis.baseline_scr == pytest.approx(0.0)  # default
        assert mis.delta_scr == pytest.approx(0.0)

    def test_mitigation_impact_summary_with_scr_fields(self):
        mis = MitigationImpactSummary(
            baseline_expected_loss=20_000_000,
            best_scenario_expected_loss=15_000_000,
            best_scenario_name="test",
            total_mitigation_cost_annual=500_000,
            net_5yr_benefit=10_000_000,
            recommended_actions=["action_a"],
            baseline_scr=100_000_000,
            best_scenario_scr=90_000_000,
            delta_scr=-10_000_000,
            baseline_tcor=20_000_000,
            best_scenario_tcor=15_500_000,
            delta_tcor=-4_500_000,
        )
        assert mis.delta_scr < 0
        assert mis.delta_tcor < 0


# ── PlatformReport extension ──────────────────────────────────────────────────

class TestPlatformReportExtension:
    def _make_minimal_report(self, **kwargs):
        return PlatformReport(
            executive_summary=ExecutiveSummary(
                operator_name="Test",
                assessment_date="2026-03-06",
                verdict="RECOMMENDED",
                composite_score=60.0,
                recommended_structure="PCC",
                expected_5yr_savings=5_000_000,
                scr_requirement=10_000_000,
                top_3_risks=["lice", "hab", "jellyfish"],
                key_actions=["action_a"],
            ),
            risk_metrics=RiskMetricsSummary(
                mean_annual_loss=20_000_000,
                var_95=60_000_000,
                var_995=100_000_000,
                tvar_95=70_000_000,
            ),
            suitability=object(),
            suitability_path=object(),
            insurance_comparison=InsuranceStructureComparison(
                strategies=[], recommended="PCC", rationale="Best value"
            ),
            **kwargs,
        )

    def test_default_optional_fields_are_none(self):
        report = self._make_minimal_report()
        assert report.capital_efficiency is None
        assert report.mitigation_impact is None
        assert report.site_risk_explanations == []

    def test_capital_efficiency_can_be_set(self):
        ces = CapitalEfficiencySummary(
            optimal_retention=5_000_000,
            minimum_tcor=20_000_000,
            current_tcor_estimate=25_000_000,
            potential_saving_nok=5_000_000,
            recommended_structure_description="XS 5M xs 5M",
        )
        report = self._make_minimal_report(capital_efficiency=ces)
        assert report.capital_efficiency is ces

    def test_mitigation_impact_can_be_set(self):
        mis = MitigationImpactSummary(
            baseline_expected_loss=20_000_000,
            best_scenario_expected_loss=15_000_000,
            best_scenario_name="lice_barriers",
            total_mitigation_cost_annual=800_000,
            net_5yr_benefit=21_000_000,
            recommended_actions=["lice_barriers"],
        )
        report = self._make_minimal_report(mitigation_impact=mis)
        assert report.mitigation_impact is mis

    def test_site_risk_explanations_can_be_set(self):
        report = self._make_minimal_report(site_risk_explanations=["expl_a", "expl_b"])
        assert len(report.site_risk_explanations) == 2

    def test_existing_fields_unchanged(self):
        report = self._make_minimal_report()
        assert report.data_confidence == "Medium"
        assert report.generated_at == ""
        assert report.mitigation_scenarios == []


# ── End-to-end integration ────────────────────────────────────────────────────

class TestEndToEndCapitalImpact:
    def test_full_pipeline_no_captive(self):
        """Analyzer → rank → summary → report, no captive structure."""
        sim = _make_sim()
        ca = MitigationCapitalAnalyzer(sim)
        impacts = ca.analyze_all_predefined()
        ranked = ca.rank_by_tcor_impact(impacts)
        summary = build_mitigation_impact_summary(ranked)
        assert summary.best_scenario_expected_loss < summary.baseline_expected_loss

    def test_full_pipeline_with_captive(self):
        """Analyzer → rank → summary → report, with captive structure."""
        sim = _make_sim()
        captive = _make_captive()
        bio_bd = _make_bio_bd(sim)
        ca = MitigationCapitalAnalyzer(sim, captive)
        impacts = ca.analyze_all_predefined(bio_loss_breakdown=bio_bd)
        ranked = ca.rank_by_suitability_impact(impacts)
        summary = build_mitigation_impact_summary(ranked)
        assert summary.delta_scr <= 0
        assert summary.delta_tcor != 0  # some change expected

    def test_single_action_end_to_end(self):
        sim = _make_sim()
        captive = _make_captive()
        ca = MitigationCapitalAnalyzer(sim, captive)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        impact = ca.analyze([action], scenario_name=action.name)
        summary = build_mitigation_impact_summary([impact])
        assert summary.best_scenario_name == action.name
        assert summary.recommended_actions == [action.name]

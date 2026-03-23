"""
Tests for the Mitigation Model (AP6).
"""
import pytest
import numpy as np
from unittest.mock import MagicMock

from analysis.mitigation import (
    MitigationAction,
    MitigationAnalyzer,
    MitigationScenario,
    PREDEFINED_MITIGATIONS,
)


def _make_sim(mean_loss=10_000_000, n=1000, t=5, seed=42):
    """Create a minimal SimulationResults mock."""
    rng = np.random.default_rng(seed)
    losses = rng.exponential(mean_loss, size=(n, t))
    sim = MagicMock()
    sim.annual_losses = losses
    sim.mean_annual_loss = float(losses.mean())
    sim.var_995 = float(np.percentile(losses.flatten(), 99.5))
    return sim


class TestMitigationAction:
    def test_combined_loss_reduction_zero_effect(self):
        action = MitigationAction(
            name="no_effect", description="", applies_to_domains=["test"]
        )
        assert action.combined_loss_reduction == 0.0

    def test_combined_loss_reduction_full_effect(self):
        action = MitigationAction(
            name="full", description="",
            applies_to_domains=["test"],
            probability_reduction=1.0,
            severity_reduction=0.0,
        )
        assert abs(action.combined_loss_reduction - 1.0) < 1e-4

    def test_combined_loss_reduction_partial(self):
        action = MitigationAction(
            name="partial", description="",
            applies_to_domains=["test"],
            probability_reduction=0.3,
            severity_reduction=0.2,
        )
        expected = 1.0 - (0.7 * 0.8)
        assert abs(action.combined_loss_reduction - expected) < 1e-4


class TestPredefinedMitigations:
    def test_all_predefined_present(self):
        expected_sea_keys = {
            "stronger_nets", "stronger_anchors", "stronger_moorings", "lice_barriers",
            "jellyfish_mitigation", "environmental_sensors",
            "storm_contingency_plan", "staff_training_program",
            "risk_manager_hire", "emergency_response_plan",
            "deformation_monitoring", "ai_early_warning",
        }
        expected_smolt_keys = {
            "smolt_oxygen_backup", "smolt_temperature_control", "smolt_co2_stripping",
            "smolt_ph_dosing", "smolt_biofilter_monitoring", "smolt_uv_sterilization",
            "smolt_backup_power", "smolt_fish_health_program", "smolt_biosecurity",
            "smolt_alarm_system", "smolt_staff_training", "smolt_emergency_plan",
        }
        assert expected_sea_keys | expected_smolt_keys == set(PREDEFINED_MITIGATIONS.keys())

    def test_facility_type_field_present(self):
        for key, action in PREDEFINED_MITIGATIONS.items():
            assert action.facility_type in ("sea", "smolt"), f"{key} has unexpected facility_type"

    def test_sea_mitigations_count(self):
        sea = [a for a in PREDEFINED_MITIGATIONS.values() if a.facility_type == "sea"]
        assert len(sea) == 12

    def test_smolt_mitigations_count(self):
        smolt = [a for a in PREDEFINED_MITIGATIONS.values() if a.facility_type == "smolt"]
        assert len(smolt) == 12

    def test_all_have_positive_cost(self):
        for key, action in PREDEFINED_MITIGATIONS.items():
            total_cost = action.annual_cost_nok + action.capex_nok
            assert total_cost > 0, f"{key} has zero cost"

    def test_reductions_bounded(self):
        for key, action in PREDEFINED_MITIGATIONS.items():
            assert 0.0 <= action.probability_reduction <= 1.0, f"{key} p_red out of bounds"
            assert 0.0 <= action.severity_reduction <= 1.0, f"{key} s_red out of bounds"


class TestMitigationAnalyzer:
    def test_empty_actions_returns_baseline(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        scenario = analyzer.compare([])
        assert abs(scenario.adjusted_expected_loss - sim.mean_annual_loss) < 1.0
        assert scenario.net_benefit_annual == 0.0

    def test_actions_reduce_expected_loss(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        scenario = analyzer.compare([action])
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_net_benefit_accounts_for_cost(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["risk_manager_hire"]
        scenario = analyzer.compare([action])
        loss_reduction = sim.mean_annual_loss - scenario.adjusted_expected_loss
        assert abs(scenario.net_benefit_annual - (loss_reduction - action.annual_cost_nok)) < 100

    def test_delta_pct_is_negative_for_effective_mitigation(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        scenario = analyzer.compare([action])
        assert scenario.delta_vs_baseline_pct < 0

    def test_compare_all_predefined(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        scenarios = analyzer.compare_all_predefined()
        # One per predefined action + one bundle
        assert len(scenarios) == len(PREDEFINED_MITIGATIONS) + 1

    def test_full_bundle_largest_reduction(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        scenarios = analyzer.compare_all_predefined()
        bundle = next(s for s in scenarios if s.name == "full_mitigation_bundle")
        individual_losses = [
            s.adjusted_expected_loss for s in scenarios
            if s.name != "full_mitigation_bundle"
        ]
        # Bundle should have lower or equal loss than each individual
        assert bundle.adjusted_expected_loss <= min(individual_losses)

    def test_scenario_fields_populated(self):
        sim = _make_sim()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        scenario = analyzer.compare([action], scenario_name="Test")
        assert isinstance(scenario, MitigationScenario)
        assert scenario.name == "Test"
        assert scenario.adjusted_scr >= 0.0
        assert scenario.annual_mitigation_cost == action.annual_cost_nok

"""
Tests for Sprint 6 – Environmental and Operational Mitigation Actions.

Verifies:
* environmental_sensors now targets hab + oxygen_stress + temperature_extreme
* storm_contingency_plan targets current_storm + ice (environmental domain)
* staff_training_program targets human_error + procedure_failure (operational domain)
* Cross-domain isolation: each new action doesn't affect other domains
* compare_all_predefined returns 11 scenarios (10 actions + bundle)
* All 10 predefined actions reduce expected loss
* Full bundle still produces largest overall reduction
"""

import warnings

import numpy as np
import pytest
from unittest.mock import MagicMock

from analysis.mitigation import (
    MitigationAction,
    MitigationAnalyzer,
    PREDEFINED_MITIGATIONS,
)
from models.domain_loss_breakdown import (
    DomainLossBreakdown,
    build_domain_loss_breakdown,
    DOMAIN_SUBTYPES,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_sim(n=400, t=5, seed=42, mean_loss=10_000_000):
    rng = np.random.default_rng(seed)
    losses = rng.exponential(mean_loss, size=(n, t))
    sim = MagicMock()
    sim.annual_losses = losses
    sim.mean_annual_loss = float(losses.mean())
    sim.var_995 = float(np.percentile(losses.flatten(), 99.5))
    return sim


def _make_domain_bd_bio_modelled(sim):
    """DomainLossBreakdown built from a C5AI+-style bio breakdown."""
    fracs = {"hab": 0.24, "lice": 0.18, "jellyfish": 0.12, "pathogen": 0.06}
    bio_bd = {rt: sim.annual_losses * f for rt, f in fracs.items()}
    return build_domain_loss_breakdown(sim.annual_losses, bio_breakdown=bio_bd)


def _make_domain_bd_prior(sim):
    """DomainLossBreakdown built from prior fractions only (no C5AI+)."""
    return build_domain_loss_breakdown(sim.annual_losses)


# ── TestEnvironmentalSensorsExtended ─────────────────────────────────────────

class TestEnvironmentalSensorsExtended:
    """environmental_sensors now targets hab + oxygen_stress + temperature_extreme."""

    def test_hab_in_targeted_risk_types(self):
        action = PREDEFINED_MITIGATIONS["environmental_sensors"]
        assert "hab" in action.targeted_risk_types

    def test_oxygen_stress_in_targeted_risk_types(self):
        action = PREDEFINED_MITIGATIONS["environmental_sensors"]
        assert "oxygen_stress" in action.targeted_risk_types

    def test_temperature_extreme_in_targeted_risk_types(self):
        action = PREDEFINED_MITIGATIONS["environmental_sensors"]
        assert "temperature_extreme" in action.targeted_risk_types

    def test_three_targeted_risk_types(self):
        action = PREDEFINED_MITIGATIONS["environmental_sensors"]
        assert len(action.targeted_risk_types) == 3

    def test_no_warning_with_domain_bd(self):
        """Should route via _apply_domain_specific, no UserWarning."""
        sim = _make_sim()
        dbd = _make_domain_bd_bio_modelled(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["environmental_sensors"]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            analyzer.compare([action], domain_loss_breakdown=dbd)

        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
        assert user_warnings == [], (
            f"Unexpected UserWarning: {[str(w.message) for w in user_warnings]}"
        )

    def test_hab_in_affected_risk_types(self):
        sim = _make_sim()
        dbd = _make_domain_bd_bio_modelled(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["environmental_sensors"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert "hab" in scenario.affected_risk_types

    def test_reduces_expected_loss(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["environmental_sensors"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss


# ── TestStormContingencyPlan ──────────────────────────────────────────────────

class TestStormContingencyPlan:
    """storm_contingency_plan targets current_storm + ice; mode=severity."""

    def test_present_in_predefined(self):
        assert "storm_contingency_plan" in PREDEFINED_MITIGATIONS

    def test_targets_current_storm(self):
        action = PREDEFINED_MITIGATIONS["storm_contingency_plan"]
        assert "current_storm" in action.targeted_risk_types

    def test_targets_ice(self):
        action = PREDEFINED_MITIGATIONS["storm_contingency_plan"]
        assert "ice" in action.targeted_risk_types

    def test_mitigation_mode_severity(self):
        action = PREDEFINED_MITIGATIONS["storm_contingency_plan"]
        assert action.mitigation_mode == "severity"

    def test_target_level_risk_type(self):
        action = PREDEFINED_MITIGATIONS["storm_contingency_plan"]
        assert action.target_level == "risk_type"

    def test_applies_to_environmental(self):
        action = PREDEFINED_MITIGATIONS["storm_contingency_plan"]
        assert "environmental" in action.applies_to_domains

    def test_no_warning_with_domain_bd(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["storm_contingency_plan"]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            analyzer.compare([action], domain_loss_breakdown=dbd)

        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
        assert user_warnings == [], (
            f"Unexpected UserWarning: {[str(w.message) for w in user_warnings]}"
        )

    def test_reduces_expected_loss(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["storm_contingency_plan"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_does_not_affect_bio_domain(self):
        """storm_contingency_plan should not appear in bio risk_type_deltas."""
        sim = _make_sim()
        dbd = _make_domain_bd_bio_modelled(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["storm_contingency_plan"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        bio_sub_types = set(DOMAIN_SUBTYPES["biological"])
        matched_bio = {k for k in scenario.risk_type_deltas if k in bio_sub_types}
        assert matched_bio == set(), (
            f"storm_contingency_plan affected bio sub-types: {matched_bio}"
        )

    def test_does_not_affect_operational_domain(self):
        """storm_contingency_plan should not appear in operational risk_type_deltas."""
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["storm_contingency_plan"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        ops_sub_types = set(DOMAIN_SUBTYPES["operational"])
        matched_ops = {k for k in scenario.risk_type_deltas if k in ops_sub_types}
        assert matched_ops == set(), (
            f"storm_contingency_plan affected operational sub-types: {matched_ops}"
        )


# ── TestStaffTrainingProgram ──────────────────────────────────────────────────

class TestStaffTrainingProgram:
    """staff_training_program targets human_error + procedure_failure; mode=both."""

    def test_present_in_predefined(self):
        assert "staff_training_program" in PREDEFINED_MITIGATIONS

    def test_targets_human_error(self):
        action = PREDEFINED_MITIGATIONS["staff_training_program"]
        assert "human_error" in action.targeted_risk_types

    def test_targets_procedure_failure(self):
        action = PREDEFINED_MITIGATIONS["staff_training_program"]
        assert "procedure_failure" in action.targeted_risk_types

    def test_mitigation_mode_both(self):
        action = PREDEFINED_MITIGATIONS["staff_training_program"]
        assert action.mitigation_mode == "both"

    def test_target_level_risk_type(self):
        action = PREDEFINED_MITIGATIONS["staff_training_program"]
        assert action.target_level == "risk_type"

    def test_applies_to_operational(self):
        action = PREDEFINED_MITIGATIONS["staff_training_program"]
        assert "operational" in action.applies_to_domains

    def test_no_warning_with_domain_bd(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["staff_training_program"]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            analyzer.compare([action], domain_loss_breakdown=dbd)

        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
        assert user_warnings == [], (
            f"Unexpected UserWarning: {[str(w.message) for w in user_warnings]}"
        )

    def test_reduces_expected_loss(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["staff_training_program"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_does_not_affect_bio_domain(self):
        """staff_training_program should not appear in bio risk_type_deltas."""
        sim = _make_sim()
        dbd = _make_domain_bd_bio_modelled(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["staff_training_program"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        bio_sub_types = set(DOMAIN_SUBTYPES["biological"])
        matched_bio = {k for k in scenario.risk_type_deltas if k in bio_sub_types}
        assert matched_bio == set(), (
            f"staff_training_program affected bio sub-types: {matched_bio}"
        )

    def test_does_not_affect_environmental_domain(self):
        """staff_training_program should not appear in environmental risk_type_deltas."""
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["staff_training_program"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        env_sub_types = set(DOMAIN_SUBTYPES["environmental"])
        matched_env = {k for k in scenario.risk_type_deltas if k in env_sub_types}
        assert matched_env == set(), (
            f"staff_training_program affected environmental sub-types: {matched_env}"
        )


# ── TestNoCrossDomainEffect ───────────────────────────────────────────────────

class TestNoCrossDomainEffect:
    """Parametrized: each new action doesn't bleed into other domains."""

    @pytest.mark.parametrize("action_name,forbidden_domain", [
        ("storm_contingency_plan", "biological"),
        ("storm_contingency_plan", "operational"),
        ("storm_contingency_plan", "structural"),
        ("staff_training_program", "biological"),
        ("staff_training_program", "environmental"),
        ("staff_training_program", "structural"),
    ])
    def test_action_does_not_affect_forbidden_domain(self, action_name, forbidden_domain):
        sim = _make_sim(seed=123)
        dbd = _make_domain_bd_bio_modelled(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS[action_name]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        forbidden_sub_types = set(DOMAIN_SUBTYPES[forbidden_domain])
        matched = {k for k in scenario.risk_type_deltas if k in forbidden_sub_types}
        assert matched == set(), (
            f"{action_name} unexpectedly affected {forbidden_domain} sub-types: {matched}"
        )


# ── TestAllPredefined10Actions ────────────────────────────────────────────────

class TestAllPredefined10Actions:
    """compare_all_predefined returns n+1 scenarios (n actions + bundle)."""

    def test_predefined_mitigations_has_12_keys(self):
        assert len(PREDEFINED_MITIGATIONS) == 12

    def test_all_expected_keys_present(self):
        expected = {
            "stronger_nets", "stronger_anchors", "stronger_moorings",
            "lice_barriers", "jellyfish_mitigation", "environmental_sensors",
            "storm_contingency_plan", "staff_training_program",
            "risk_manager_hire", "emergency_response_plan",
            "deformation_monitoring", "ai_early_warning",
        }
        assert expected == set(PREDEFINED_MITIGATIONS.keys())

    def test_compare_all_predefined_returns_13_scenarios(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        scenarios = analyzer.compare_all_predefined(domain_loss_breakdown=dbd)
        # 12 predefined + 1 bundle
        assert len(scenarios) == 13

    def test_no_user_warnings_with_full_domain_bd(self):
        """All 10 actions should route cleanly when domain_bd is provided."""
        sim = _make_sim()
        dbd = _make_domain_bd_bio_modelled(sim)
        analyzer = MitigationAnalyzer(sim)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            analyzer.compare_all_predefined(domain_loss_breakdown=dbd)

        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
        assert user_warnings == [], (
            f"Unexpected UserWarnings: {[str(w.message) for w in user_warnings]}"
        )

    def test_all_individual_actions_reduce_loss(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        scenarios = analyzer.compare_all_predefined(domain_loss_breakdown=dbd)
        individual = [s for s in scenarios if s.name != "full_mitigation_bundle"]
        for s in individual:
            assert s.adjusted_expected_loss < sim.mean_annual_loss, (
                f"Action {s.name!r} did not reduce expected loss"
            )

    def test_bundle_achieves_larger_reduction_than_any_individual(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        scenarios = analyzer.compare_all_predefined(domain_loss_breakdown=dbd)
        bundle = next(s for s in scenarios if s.name == "full_mitigation_bundle")
        individual = [s for s in scenarios if s.name != "full_mitigation_bundle"]
        best_individual_loss = min(s.adjusted_expected_loss for s in individual)
        assert bundle.adjusted_expected_loss <= best_individual_loss + 1.0, (
            "Bundle should achieve equal or lower loss than any individual action"
        )

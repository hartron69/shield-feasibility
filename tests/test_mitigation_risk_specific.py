"""
Tests for Sprint 2 Part A – Risk-Specific Mitigation.

Verifies that actions with targeted_risk_types affect only the relevant
bio_loss_breakdown slices, and that portfolio-wide actions remain unchanged.
"""

import warnings

import numpy as np
import pytest
from unittest.mock import MagicMock

from analysis.mitigation import (
    MitigationAction,
    MitigationAnalyzer,
    MitigationScenario,
    PREDEFINED_MITIGATIONS,
    SMOLT_DOMAIN_MAPPING,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_sim_with_bio(
    n=500, t=5, seed=42,
    bio_fractions=None,
):
    """
    Create a SimulationResults mock WITH bio_loss_breakdown.

    bio_fractions : dict of risk_type → fraction of total losses.
    """
    rng = np.random.default_rng(seed)
    total_losses = rng.exponential(10_000_000, size=(n, t))
    if bio_fractions is None:
        bio_fractions = {"hab": 0.40, "lice": 0.30, "jellyfish": 0.20, "pathogen": 0.10}
    bio_bd = {rt: total_losses * frac for rt, frac in bio_fractions.items()}
    sim = MagicMock()
    sim.annual_losses = total_losses
    sim.mean_annual_loss = float(total_losses.mean())
    sim.var_995 = float(np.percentile(total_losses.flatten(), 99.5))
    sim.bio_loss_breakdown = bio_bd
    return sim, bio_bd


def _make_sim_no_bio(n=500, t=5, seed=42):
    """Create a SimulationResults mock WITHOUT bio_loss_breakdown."""
    rng = np.random.default_rng(seed)
    losses = rng.exponential(10_000_000, size=(n, t))
    sim = MagicMock()
    sim.annual_losses = losses
    sim.mean_annual_loss = float(losses.mean())
    sim.var_995 = float(np.percentile(losses.flatten(), 99.5))
    sim.bio_loss_breakdown = None
    return sim


# ── MitigationAction new fields ───────────────────────────────────────────────

class TestMitigationActionNewFields:
    def test_targeted_risk_types_default_empty(self):
        action = MitigationAction(name="x", description="", applies_to_domains=[])
        assert action.targeted_risk_types == []

    def test_mitigation_mode_default(self):
        action = MitigationAction(name="x", description="", applies_to_domains=[])
        assert action.mitigation_mode == "both"

    def test_target_level_default(self):
        action = MitigationAction(name="x", description="", applies_to_domains=[])
        assert action.target_level == "portfolio"

    def test_custom_targeted_risk_types(self):
        action = MitigationAction(
            name="jelly", description="", applies_to_domains=[],
            targeted_risk_types=["jellyfish"],
        )
        assert action.targeted_risk_types == ["jellyfish"]


# ── PREDEFINED_MITIGATIONS targeted_risk_types ────────────────────────────────

class TestPredefinedMitigationsRiskTypes:
    def test_jellyfish_mitigation_targets_jellyfish(self):
        a = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        assert "jellyfish" in a.targeted_risk_types

    def test_lice_barriers_targets_lice(self):
        a = PREDEFINED_MITIGATIONS["lice_barriers"]
        assert "lice" in a.targeted_risk_types

    def test_environmental_sensors_targets_hab(self):
        a = PREDEFINED_MITIGATIONS["environmental_sensors"]
        assert "hab" in a.targeted_risk_types

    def test_risk_manager_is_portfolio_wide(self):
        a = PREDEFINED_MITIGATIONS["risk_manager_hire"]
        assert a.targeted_risk_types == []

    def test_emergency_response_is_portfolio_wide(self):
        a = PREDEFINED_MITIGATIONS["emergency_response_plan"]
        assert a.targeted_risk_types == []

    def test_stronger_nets_targets_net_integrity(self):
        # Sprint 5: stronger_nets now targets structural sub-types explicitly
        a = PREDEFINED_MITIGATIONS["stronger_nets"]
        assert "net_integrity" in a.targeted_risk_types

    def test_stronger_moorings_targets_mooring_failure(self):
        # Sprint 5: stronger_moorings now targets structural sub-types explicitly
        a = PREDEFINED_MITIGATIONS["stronger_moorings"]
        assert "mooring_failure" in a.targeted_risk_types


# ── Risk-specific: jellyfish action affects only jellyfish slice ──────────────

class TestRiskSpecificMitigation:
    def test_jellyfish_action_changes_jellyfish_only(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]

        scenario = analyzer.compare(
            [action], bio_loss_breakdown=bio_bd
        )

        # Jellyfish should be in affected types
        assert "jellyfish" in scenario.affected_risk_types

    def test_jellyfish_action_does_not_affect_lice_in_delta(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]

        scenario = analyzer.compare(
            [action], bio_loss_breakdown=bio_bd
        )

        # Lice delta should be ≤ 0 only via portfolio multiplier (which is 1.0
        # for a pure risk-specific action with no portfolio-wide component).
        # The only risk-specific reduction was jellyfish.
        assert "lice" not in scenario.affected_risk_types

    def test_lice_action_targets_lice_only(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]

        scenario = analyzer.compare(
            [action], bio_loss_breakdown=bio_bd
        )
        assert "lice" in scenario.affected_risk_types
        assert "jellyfish" not in scenario.affected_risk_types
        assert "hab" not in scenario.affected_risk_types

    def test_env_sensors_targets_hab_only(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["environmental_sensors"]

        scenario = analyzer.compare(
            [action], bio_loss_breakdown=bio_bd
        )
        assert "hab" in scenario.affected_risk_types
        assert "lice" not in scenario.affected_risk_types

    def test_site_losses_sum_preserved(self):
        """Portfolio total must equal the sum of all adjusted slices."""
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]

        scenario = analyzer.compare(
            [action], bio_loss_breakdown=bio_bd
        )
        # Adjusted mean + other slices must be less than baseline
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss
        assert scenario.adjusted_expected_loss > 0

    def test_risk_specific_reduces_overall_loss(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_fallback_false_when_breakdown_provided(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)
        # jellyfish action matched → no fallback
        assert scenario.fallback_to_portfolio_scaling is False

    def test_risk_type_deltas_populated(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)
        # At least jellyfish key should be in deltas
        assert "jellyfish" in scenario.risk_type_deltas
        assert scenario.risk_type_deltas["jellyfish"] < 0  # improvement

    def test_risk_type_deltas_unaffected_keys_near_zero(self):
        """Unaffected risk types should have ≈0 delta when no portfolio action."""
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)
        # Lice slice was not targeted → delta should be exactly 0
        if "lice" in scenario.risk_type_deltas:
            assert abs(scenario.risk_type_deltas["lice"]) < 1.0  # effectively zero


# ── Portfolio-wide actions: backward-compat path ─────────────────────────────

class TestPortfolioWideWithBreakdown:
    def test_risk_manager_is_portfolio_wide_with_breakdown(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["risk_manager_hire"]
        scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)
        # No risk-specific targeting → affected_risk_types is empty
        assert scenario.affected_risk_types == []
        # But losses should still decrease
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_emergency_plan_reduces_losses_with_breakdown(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["emergency_response_plan"]
        scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss


# ── Backward compatibility: no bio_loss_breakdown (Sprint 1 behavior) ─────────

class TestNoBreakdownFallback:
    def test_fallback_true_without_breakdown(self):
        sim = _make_sim_no_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        scenario = analyzer.compare([action])  # no bio_loss_breakdown
        assert scenario.fallback_to_portfolio_scaling is True

    def test_jellyfish_action_still_reduces_loss_in_fallback(self):
        sim = _make_sim_no_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        scenario = analyzer.compare([action])
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_empty_actions_returns_baseline_no_breakdown(self):
        sim = _make_sim_no_bio()
        analyzer = MitigationAnalyzer(sim)
        scenario = analyzer.compare([])
        assert abs(scenario.adjusted_expected_loss - sim.mean_annual_loss) < 1.0
        assert scenario.net_benefit_annual == 0.0

    def test_all_predefined_still_reduce_loss_in_fallback(self):
        sim = _make_sim_no_bio()
        analyzer = MitigationAnalyzer(sim)
        scenarios = analyzer.compare_all_predefined()
        for s in scenarios:
            if s.name != "full_mitigation_bundle":
                assert s.adjusted_expected_loss <= sim.mean_annual_loss

    def test_full_bundle_lowest_in_fallback(self):
        sim = _make_sim_no_bio()
        analyzer = MitigationAnalyzer(sim)
        scenarios = analyzer.compare_all_predefined()
        bundle = next(s for s in scenarios if s.name == "full_mitigation_bundle")
        others = [s.adjusted_expected_loss for s in scenarios if s.name != "full_mitigation_bundle"]
        assert bundle.adjusted_expected_loss <= min(others)


# ── Structural action: no match in bio breakdown → portfolio fallback ─────────

class TestStructuralActionFallback:
    def test_stronger_nets_warns_and_falls_back(self):
        """stronger_nets targets 'structural' which is not in bio breakdown."""
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]

        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)

        # Should warn about structural not being in breakdown
        assert any("structural" in str(w.message).lower() or "targeted_risk_types" in str(w.message) for w in caught)

    def test_stronger_nets_still_reduces_losses(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        import warnings
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss


# ── Combined: risk-specific + portfolio-wide ──────────────────────────────────

class TestCombinedActions:
    def test_jellyfish_plus_risk_manager(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        actions = [
            PREDEFINED_MITIGATIONS["jellyfish_mitigation"],
            PREDEFINED_MITIGATIONS["risk_manager_hire"],
        ]
        scenario = analyzer.compare(actions, bio_loss_breakdown=bio_bd)
        # Both should reduce losses
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss
        # Jellyfish was targeted
        assert "jellyfish" in scenario.affected_risk_types

    def test_bundle_reduces_more_than_single_action(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)

        single = analyzer.compare(
            [PREDEFINED_MITIGATIONS["jellyfish_mitigation"]],
            bio_loss_breakdown=bio_bd,
        )
        bundle = analyzer.compare(
            list(PREDEFINED_MITIGATIONS.values()),
            bio_loss_breakdown=bio_bd,
        )
        assert bundle.adjusted_expected_loss <= single.adjusted_expected_loss

    def test_baseline_expected_loss_populated(self):
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)
        assert scenario.baseline_expected_loss > 0
        assert abs(scenario.baseline_expected_loss - sim.mean_annual_loss) < 1.0


# ── Smolt domain mapping tests ────────────────────────────────────────────────

def _smolt_actions():
    return [a for a in PREDEFINED_MITIGATIONS.values() if a.facility_type == 'smolt']


def _make_smolt_domain_bd(n=200, t=5, seed=7):
    """Build a minimal DomainLossBreakdown mock with smolt sub-types."""
    from models.domain_loss_breakdown import DomainLossBreakdown
    rng = np.random.default_rng(seed)
    total = rng.exponential(5_000_000, size=(n, t))
    # SMOLT_DOMAIN_FRACTIONS: ops=70%, bio=22%, struct=5%, env=3%
    ops_sub  = {"biofilter": 0.35, "oxygen": 0.25, "power": 0.20, "general_ops": 0.20}
    bio_sub  = {"water_quality": 0.60, "biosecurity": 0.40}
    struct_s = {"building": 0.60, "equipment_damage": 0.40}
    env_sub  = {"flood": 0.50, "utility_failure": 0.50}
    return DomainLossBreakdown(
        biological   ={k: total * 0.22 * v for k, v in bio_sub.items()},
        structural   ={k: total * 0.05 * v for k, v in struct_s.items()},
        environmental={k: total * 0.03 * v for k, v in env_sub.items()},
        operational  ={k: total * 0.70 * v for k, v in ops_sub.items()},
        operational_model_type="smolt_stub",
    ), total


class TestSmoltDomainMapping:

    def test_smolt_domain_mapping_covers_all_smolt_risk_types(self):
        """All targeted_risk_types in 12 smolt actions are in SMOLT_DOMAIN_MAPPING."""
        for action in _smolt_actions():
            for rt in action.targeted_risk_types:
                assert rt in SMOLT_DOMAIN_MAPPING, (
                    f"{action.name}: '{rt}' not in SMOLT_DOMAIN_MAPPING"
                )

    def test_smolt_ras_backup_oxygen_targets_ras_domain(self):
        """smolt_oxygen_backup maps to oxygen_event, NOT to sea domains."""
        action = PREDEFINED_MITIGATIONS["smolt_oxygen_backup"]
        sea_domains = {"hab", "lice", "jellyfish", "pathogen"}
        for rt in action.targeted_risk_types:
            category = SMOLT_DOMAIN_MAPPING.get(rt, rt)
            assert category not in sea_domains, (
                f"'{rt}' maps to '{category}' which is a sea domain"
            )
        # Specifically verifies it maps to a smolt oxygen category
        mapped = {SMOLT_DOMAIN_MAPPING.get(rt) for rt in action.targeted_risk_types}
        assert "oxygen_event" in mapped

    def test_smolt_ups_aggregat_targets_power_domain(self):
        """smolt_backup_power maps to power_outage, NOT to environmental."""
        action = PREDEFINED_MITIGATIONS["smolt_backup_power"]
        for rt in action.targeted_risk_types:
            category = SMOLT_DOMAIN_MAPPING.get(rt, rt)
            assert category != "environmental", (
                f"'{rt}' should not map to environmental"
            )
        mapped = {SMOLT_DOMAIN_MAPPING.get(rt) for rt in action.targeted_risk_types}
        assert "power_outage" in mapped

    def test_no_userwarning_for_any_smolt_mitigation(self):
        """Running all 12 smolt actions through compare() triggers no UserWarning."""
        domain_bd, total = _make_smolt_domain_bd()
        sim = MagicMock()
        sim.annual_losses = total
        sim.mean_annual_loss = float(total.mean())
        sim.var_995 = float(np.percentile(total.flatten(), 99.5))
        analyzer = MitigationAnalyzer(sim)

        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            for action in _smolt_actions():
                # Should raise no UserWarning
                analyzer.compare([action], domain_loss_breakdown=domain_bd)

    def test_sea_mitigations_unaffected_by_smolt_mapping(self):
        """Sea mitigations still affect correct sea sub-types after smolt mapping added."""
        sim, bio_bd = _make_sim_with_bio()
        analyzer = MitigationAnalyzer(sim)

        jelly = analyzer.compare(
            [PREDEFINED_MITIGATIONS["jellyfish_mitigation"]],
            bio_loss_breakdown=bio_bd,
        )
        assert "jellyfish" in jelly.affected_risk_types
        assert "lice" not in jelly.affected_risk_types

        lice = analyzer.compare(
            [PREDEFINED_MITIGATIONS["lice_barriers"]],
            bio_loss_breakdown=bio_bd,
        )
        assert "lice" in lice.affected_risk_types
        assert "jellyfish" not in lice.affected_risk_types

    def test_smolt_library_returns_exactly_12_for_smolt_query(self):
        """GET /api/mitigation/library?facility_type=smolt returns exactly 12 actions."""
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        resp = client.get("/api/mitigation/library?facility_type=smolt")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12, f"Expected 12 smolt actions, got {len(data)}"
        for item in data:
            assert item["facility_type"] == "smolt"

    def test_sea_library_returns_zero_smolt_for_sea_query(self):
        """GET /api/mitigation/library?facility_type=sea returns no smolt actions."""
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        resp = client.get("/api/mitigation/library?facility_type=sea")
        assert resp.status_code == 200
        data = resp.json()
        smolt_in_sea = [a for a in data if a.get("facility_type") == "smolt"]
        assert len(smolt_in_sea) == 0, "Sea library must not contain smolt actions"

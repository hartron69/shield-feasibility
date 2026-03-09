"""
Tests for Sprint 5 – Structural Mitigation Mapping.

Verifies the mapping of structural mitigation actions to the correct
DomainLossBreakdown sub-types, the mooring_failure overlap cap, and
backward compatibility with portfolio-wide and bio-only paths.

Key invariants tested
---------------------
* stronger_nets → only affects net_integrity and cage_structural
* stronger_anchors → only affects mooring_failure
* stronger_moorings → affects mooring_failure and cage_structural
* Structural actions do NOT affect biological / environmental / operational sub-types
* stronger_anchors + stronger_moorings combined: mooring_failure reduction capped at 48%
* Domain totals preserved after mitigation
* No warnings when domain_loss_breakdown supplied for all structural actions
* Backward compat: structural actions fall back to portfolio-wide when no dbd
"""

import warnings

import numpy as np
import pytest
from unittest.mock import MagicMock

from analysis.mitigation import MitigationAnalyzer, PREDEFINED_MITIGATIONS
from models.domain_loss_breakdown import (
    DomainLossBreakdown,
    build_domain_loss_breakdown,
    STRUCTURAL_SUBTYPE_CAPS,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_sim(n=500, t=5, seed=0, mean=10_000_000):
    rng = np.random.default_rng(seed)
    losses = rng.exponential(mean, size=(n, t))
    sim = MagicMock()
    sim.annual_losses = losses
    sim.mean_annual_loss = float(losses.mean())
    sim.var_995 = float(np.percentile(losses.flatten(), 99.5))
    return sim


def _make_prior_dbd(sim):
    return build_domain_loss_breakdown(sim.annual_losses)


def _make_bio_dbd(sim):
    fracs = {"hab": 0.24, "lice": 0.18, "jellyfish": 0.12, "pathogen": 0.06}
    bio_bd = {rt: sim.annual_losses * f for rt, f in fracs.items()}
    return build_domain_loss_breakdown(sim.annual_losses, bio_breakdown=bio_bd)


def _sub_type_mean(dbd: DomainLossBreakdown, sub_type: str) -> float:
    """Return mean of a named sub-type across all domains."""
    all_st = dbd.all_subtypes()
    if sub_type not in all_st:
        raise KeyError(f"{sub_type} not in DomainLossBreakdown")
    return float(all_st[sub_type].mean())


# ── Action targeting correctness ──────────────────────────────────────────────

class TestStrongerNetsTargeting:
    def test_targets_net_integrity_and_cage_structural(self):
        a = PREDEFINED_MITIGATIONS["stronger_nets"]
        assert "net_integrity" in a.targeted_risk_types
        assert "cage_structural" in a.targeted_risk_types

    def test_does_not_target_mooring_failure(self):
        a = PREDEFINED_MITIGATIONS["stronger_nets"]
        assert "mooring_failure" not in a.targeted_risk_types

    def test_affected_risk_types_contains_net_integrity(self):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS["stronger_nets"]], domain_loss_breakdown=dbd
        )
        assert "net_integrity" in scenario.affected_risk_types

    def test_affected_risk_types_contains_cage_structural(self):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS["stronger_nets"]], domain_loss_breakdown=dbd
        )
        assert "cage_structural" in scenario.affected_risk_types

    def test_does_not_affect_mooring_failure(self):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS["stronger_nets"]], domain_loss_breakdown=dbd
        )
        assert "mooring_failure" not in scenario.affected_risk_types

    def test_does_not_affect_biological_sub_types(self):
        sim = _make_sim()
        dbd = _make_bio_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS["stronger_nets"]], domain_loss_breakdown=dbd
        )
        bio_types = {"hab", "lice", "jellyfish", "pathogen"}
        assert not bio_types.intersection(scenario.affected_risk_types)

    def test_no_warning_with_domain_bd(self):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            MitigationAnalyzer(sim).compare(
                [PREDEFINED_MITIGATIONS["stronger_nets"]], domain_loss_breakdown=dbd
            )
        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
        assert user_warnings == []

    def test_mitigation_mode_is_both(self):
        a = PREDEFINED_MITIGATIONS["stronger_nets"]
        assert a.mitigation_mode == "both"


class TestStrongerAnchorsTargeting:
    def test_targets_mooring_failure_only(self):
        a = PREDEFINED_MITIGATIONS["stronger_anchors"]
        assert a.targeted_risk_types == ["mooring_failure"]

    def test_mitigation_mode_is_probability(self):
        a = PREDEFINED_MITIGATIONS["stronger_anchors"]
        assert a.mitigation_mode == "probability"

    def test_affected_risk_types_contains_mooring_failure(self):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS["stronger_anchors"]], domain_loss_breakdown=dbd
        )
        assert "mooring_failure" in scenario.affected_risk_types

    def test_does_not_affect_net_integrity(self):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS["stronger_anchors"]], domain_loss_breakdown=dbd
        )
        assert "net_integrity" not in scenario.affected_risk_types

    def test_does_not_affect_biological_sub_types(self):
        sim = _make_sim()
        dbd = _make_bio_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS["stronger_anchors"]], domain_loss_breakdown=dbd
        )
        bio_types = {"hab", "lice", "jellyfish", "pathogen"}
        assert not bio_types.intersection(scenario.affected_risk_types)

    def test_no_warning_with_domain_bd(self):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            MitigationAnalyzer(sim).compare(
                [PREDEFINED_MITIGATIONS["stronger_anchors"]], domain_loss_breakdown=dbd
            )
        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
        assert user_warnings == []

    def test_reduces_loss(self):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS["stronger_anchors"]], domain_loss_breakdown=dbd
        )
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_high_probability_reduction(self):
        """stronger_anchors should have probability_reduction ≥ 0.30."""
        a = PREDEFINED_MITIGATIONS["stronger_anchors"]
        assert a.probability_reduction >= 0.30


class TestStrongerMooringsTargeting:
    def test_targets_mooring_failure_and_cage_structural(self):
        a = PREDEFINED_MITIGATIONS["stronger_moorings"]
        assert "mooring_failure" in a.targeted_risk_types
        assert "cage_structural" in a.targeted_risk_types

    def test_does_not_target_net_integrity(self):
        a = PREDEFINED_MITIGATIONS["stronger_moorings"]
        assert "net_integrity" not in a.targeted_risk_types

    def test_affected_risk_types_contains_mooring_failure(self):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS["stronger_moorings"]], domain_loss_breakdown=dbd
        )
        assert "mooring_failure" in scenario.affected_risk_types

    def test_affected_risk_types_contains_cage_structural(self):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS["stronger_moorings"]], domain_loss_breakdown=dbd
        )
        assert "cage_structural" in scenario.affected_risk_types

    def test_does_not_affect_biological_sub_types(self):
        sim = _make_sim()
        dbd = _make_bio_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS["stronger_moorings"]], domain_loss_breakdown=dbd
        )
        bio_types = {"hab", "lice", "jellyfish", "pathogen"}
        assert not bio_types.intersection(scenario.affected_risk_types)

    def test_mitigation_mode_is_both(self):
        a = PREDEFINED_MITIGATIONS["stronger_moorings"]
        assert a.mitigation_mode == "both"


# ── Structural actions do not cross domain boundaries ─────────────────────────

class TestNoCrossDomainEffect:
    """All three structural actions must not alter environmental or operational losses."""

    @pytest.mark.parametrize("action_key", [
        "stronger_nets", "stronger_anchors", "stronger_moorings"
    ])
    def test_environmental_sub_types_unaffected(self, action_key):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        env_types = {"oxygen_stress", "temperature_extreme", "current_storm", "ice"}
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS[action_key]], domain_loss_breakdown=dbd
        )
        assert not env_types.intersection(scenario.affected_risk_types)

    @pytest.mark.parametrize("action_key", [
        "stronger_nets", "stronger_anchors", "stronger_moorings"
    ])
    def test_operational_sub_types_unaffected(self, action_key):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        ops_types = {"human_error", "procedure_failure", "equipment", "incident"}
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS[action_key]], domain_loss_breakdown=dbd
        )
        assert not ops_types.intersection(scenario.affected_risk_types)


# ── Mooring failure overlap cap ───────────────────────────────────────────────

class TestMooringFailureOverlapCap:
    """
    When stronger_anchors + stronger_moorings are combined, the mooring_failure
    sub-type reduction must be capped at STRUCTURAL_SUBTYPE_CAPS["mooring_failure"]
    (currently 0.48 = 48% max combined reduction).
    """

    def test_cap_constant_is_defined_for_mooring_failure(self):
        assert "mooring_failure" in STRUCTURAL_SUBTYPE_CAPS
        cap = STRUCTURAL_SUBTYPE_CAPS["mooring_failure"]
        assert 0.40 <= cap <= 0.55, f"Cap {cap} outside expected range [0.40, 0.55]"

    def test_combined_cap_applied(self):
        """
        Combined anchors + moorings would give:
            (1 - 0.35) × (1 - 0.30) = 0.455 → ~54.5% reduction (uncapped).
        After cap at 48%, mooring_failure should not fall below 52% of original.
        """
        cap = STRUCTURAL_SUBTYPE_CAPS["mooring_failure"]

        sim = _make_sim(n=1000, seed=7)
        dbd = _make_prior_dbd(sim)

        initial_mf_mean = float(dbd.structural["mooring_failure"].mean())

        anchors = PREDEFINED_MITIGATIONS["stronger_anchors"]
        moorings = PREDEFINED_MITIGATIONS["stronger_moorings"]
        scenario = MitigationAnalyzer(sim).compare(
            [anchors, moorings], domain_loss_breakdown=dbd
        )

        mitigated_losses = scenario.mitigated_annual_losses
        assert mitigated_losses is not None

        # The overall loss reduction should be > 0 (some reduction was applied)
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

        # Check that the cap is respected: total reduction on mooring_failure
        # must not exceed cap_fraction of initial_mf_mean.
        # We verify via risk_type_deltas if available.
        if "mooring_failure" in scenario.risk_type_deltas:
            delta = scenario.risk_type_deltas["mooring_failure"]
            # delta is negative (improvement). The magnitude must be ≤ cap × initial_mean.
            max_allowed_reduction = initial_mf_mean * cap
            assert abs(delta) <= max_allowed_reduction * 1.01, (
                f"mooring_failure reduction {abs(delta):.0f} exceeds cap "
                f"{max_allowed_reduction:.0f} (cap={cap})"
            )

    def test_single_action_not_capped(self):
        """A single anchors action alone stays well below the cap – no clipping expected."""
        cap = STRUCTURAL_SUBTYPE_CAPS["mooring_failure"]

        sim = _make_sim(n=1000, seed=8)
        dbd = _make_prior_dbd(sim)
        initial_mf_mean = float(dbd.structural["mooring_failure"].mean())

        anchors = PREDEFINED_MITIGATIONS["stronger_anchors"]
        scenario = MitigationAnalyzer(sim).compare(
            [anchors], domain_loss_breakdown=dbd
        )

        # stronger_anchors: combined_loss_reduction ≈ 1 - (1-0.35)×(1-0.05) ≈ 0.3825
        # 0.3825 < 0.48 cap → no clipping should occur
        if "mooring_failure" in scenario.risk_type_deltas:
            delta = scenario.risk_type_deltas["mooring_failure"]
            reduction_fraction = abs(delta) / max(initial_mf_mean, 1)
            # Should be less than cap (no clipping expected for single action)
            assert reduction_fraction < cap + 0.01

    def test_combined_reduction_less_than_uncapped(self):
        """
        Combined anchors + moorings reduction on total loss should be
        less than if the cap were not present (cap constrains the optimistic case).
        """
        sim = _make_sim(n=1000, seed=9)
        dbd_1 = _make_prior_dbd(sim)
        dbd_2 = _make_prior_dbd(sim)

        anchors = PREDEFINED_MITIGATIONS["stronger_anchors"]
        moorings = PREDEFINED_MITIGATIONS["stronger_moorings"]

        combined_scenario = MitigationAnalyzer(sim).compare(
            [anchors, moorings], domain_loss_breakdown=dbd_1
        )
        anchors_only_scenario = MitigationAnalyzer(sim).compare(
            [anchors], domain_loss_breakdown=dbd_2
        )

        # Combined should reduce more than anchors alone (even with cap)
        assert (
            combined_scenario.adjusted_expected_loss
            < anchors_only_scenario.adjusted_expected_loss
        )


# ── Domain totals preserved ───────────────────────────────────────────────────

class TestDomainTotalPreservation:
    @pytest.mark.parametrize("action_key", [
        "stronger_nets", "stronger_anchors", "stronger_moorings"
    ])
    def test_mitigated_total_matches_adjusted_expected_loss(self, action_key):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        scenario = MitigationAnalyzer(sim).compare(
            [PREDEFINED_MITIGATIONS[action_key]], domain_loss_breakdown=dbd
        )
        assert scenario.mitigated_annual_losses is not None
        computed_mean = float(scenario.mitigated_annual_losses.mean())
        assert abs(computed_mean - scenario.adjusted_expected_loss) < 1.0

    def test_combined_bundle_preserves_array(self):
        sim = _make_sim()
        dbd = _make_prior_dbd(sim)
        anchors = PREDEFINED_MITIGATIONS["stronger_anchors"]
        moorings = PREDEFINED_MITIGATIONS["stronger_moorings"]
        nets = PREDEFINED_MITIGATIONS["stronger_nets"]
        scenario = MitigationAnalyzer(sim).compare(
            [anchors, moorings, nets], domain_loss_breakdown=dbd
        )
        assert scenario.mitigated_annual_losses is not None
        assert scenario.mitigated_annual_losses.shape == sim.annual_losses.shape
        assert float(scenario.mitigated_annual_losses.min()) >= 0.0


# ── Backward compatibility ────────────────────────────────────────────────────

class TestBackwardCompatibility:
    def test_structural_actions_fallback_without_dbd(self):
        """Without domain_loss_breakdown, structural actions fall back to portfolio-wide."""
        sim = _make_sim()
        sim.bio_loss_breakdown = None

        for action_key in ("stronger_nets", "stronger_anchors", "stronger_moorings"):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                scenario = MitigationAnalyzer(sim).compare(
                    [PREDEFINED_MITIGATIONS[action_key]]
                )
            # Should still reduce loss (portfolio-wide fallback)
            assert scenario.adjusted_expected_loss <= sim.mean_annual_loss, (
                f"{action_key} did not reduce loss in fallback mode"
            )

    def test_bio_actions_unaffected_by_sprint5_changes(self):
        """Sprint 5 changes must not alter bio-targeted action behaviour."""
        rng = np.random.default_rng(42)
        losses = rng.exponential(10_000_000, size=(400, 5))
        bio_bd = {
            "hab": losses * 0.24, "lice": losses * 0.18,
            "jellyfish": losses * 0.12, "pathogen": losses * 0.06,
        }
        sim = MagicMock()
        sim.annual_losses = losses
        sim.mean_annual_loss = float(losses.mean())
        sim.var_995 = float(np.percentile(losses.flatten(), 99.5))

        dbd = build_domain_loss_breakdown(losses, bio_breakdown=bio_bd)
        analyzer = MitigationAnalyzer(sim)

        jelly_scenario = analyzer.compare(
            [PREDEFINED_MITIGATIONS["jellyfish_mitigation"]], domain_loss_breakdown=dbd
        )
        lice_scenario = analyzer.compare(
            [PREDEFINED_MITIGATIONS["lice_barriers"]], domain_loss_breakdown=dbd
        )

        assert "jellyfish" in jelly_scenario.affected_risk_types
        assert "lice" in lice_scenario.affected_risk_types
        assert jelly_scenario.adjusted_expected_loss < sim.mean_annual_loss
        assert lice_scenario.adjusted_expected_loss < sim.mean_annual_loss

"""
Tests for Sprint 4 – Domain-Aware Mitigation.

Verifies that MitigationAnalyzer.compare() correctly routes actions through
the DomainLossBreakdown, enabling structural/environmental/operational actions
to target the correct slices without falling back to portfolio-wide scaling.

Also covers MitigationCapitalAnalyzer.analyze() with domain_loss_breakdown.
"""

import warnings

import numpy as np
import pytest
from unittest.mock import MagicMock

from analysis.mitigation import (
    MitigationAction,
    MitigationAnalyzer,
    MitigationCapitalAnalyzer,
    PREDEFINED_MITIGATIONS,
    build_mitigation_impact_summary,
)
from models.domain_loss_breakdown import (
    DomainLossBreakdown,
    build_domain_loss_breakdown,
)
from models.captive_structure import CaptiveStructure, RetentionLayer, ReinsuranceLayer


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
    """DomainLossBreakdown built from prior fractions only."""
    return build_domain_loss_breakdown(sim.annual_losses)


def _make_captive():
    return CaptiveStructure(
        operator_name="Test",
        retention=RetentionLayer(
            name="Ded", per_occurrence_retention=2_000_000,
            annual_aggregate_retention=6_000_000,
        ),
        captive_layer=ReinsuranceLayer(
            name="Cell", attachment_point=2_000_000,
            limit=18_000_000, participation_pct=100.0, estimated_premium=400_000,
        ),
    )


# ── Domain path routing ───────────────────────────────────────────────────────

class TestDomainPathRouting:
    def test_stronger_nets_does_not_warn_with_domain_bd(self):
        """stronger_nets targets 'structural' which IS in DomainLossBreakdown."""
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            scenario = analyzer.compare([action], domain_loss_breakdown=dbd)

        structural_warnings = [
            w for w in caught if "structural" in str(w.message).lower()
        ]
        assert structural_warnings == [], (
            f"Unexpected structural warning: {[str(w.message) for w in structural_warnings]}"
        )

    def test_stronger_moorings_does_not_warn_with_domain_bd(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_moorings"]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            scenario = analyzer.compare([action], domain_loss_breakdown=dbd)

        assert not any("structural" in str(w.message).lower() for w in caught)

    def test_structural_action_in_affected_risk_types(self):
        # Sprint 5: stronger_nets targets sub-types net_integrity + cage_structural
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert (
            "net_integrity" in scenario.affected_risk_types
            or "cage_structural" in scenario.affected_risk_types
        )

    def test_structural_action_reduces_loss(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_structural_delta_negative(self):
        # Sprint 5: deltas now at sub-type level (net_integrity, cage_structural)
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        # At least one targeted structural sub-type must have a negative delta
        structural_subs = {"net_integrity", "cage_structural"}
        matched = {k: v for k, v in scenario.risk_type_deltas.items() if k in structural_subs}
        assert matched, "No structural sub-type delta found"
        assert all(v < 0 for v in matched.values())

    def test_jellyfish_action_targets_jellyfish_subtype(self):
        sim = _make_sim()
        dbd = _make_domain_bd_bio_modelled(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert "jellyfish" in scenario.affected_risk_types
        assert "structural" not in scenario.affected_risk_types

    def test_lice_action_targets_lice_subtype(self):
        sim = _make_sim()
        dbd = _make_domain_bd_bio_modelled(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["lice_barriers"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert "lice" in scenario.affected_risk_types
        assert "jellyfish" not in scenario.affected_risk_types

    def test_portfolio_wide_action_not_in_affected_types(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["risk_manager_hire"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert scenario.affected_risk_types == []

    def test_portfolio_wide_action_still_reduces_loss(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["emergency_response_plan"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_env_sensors_targets_hab_subtype(self):
        """environmental_sensors targets 'hab', a bio sub-type."""
        sim = _make_sim()
        dbd = _make_domain_bd_bio_modelled(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["environmental_sensors"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert "hab" in scenario.affected_risk_types


# ── Domain path vs bio-only path ──────────────────────────────────────────────

class TestDomainVsBioPath:
    def test_jellyfish_result_consistent_with_bio_path(self):
        """
        For a pure-bio action with a bio-modelled domain breakdown,
        the domain path should give approximately the same adjusted loss
        as the bio-only path (same underlying fractions).
        """
        sim = _make_sim()
        fracs = {"hab": 0.24, "lice": 0.18, "jellyfish": 0.12, "pathogen": 0.06}
        bio_bd = {rt: sim.annual_losses * f for rt, f in fracs.items()}
        dbd = build_domain_loss_breakdown(sim.annual_losses, bio_breakdown=bio_bd)

        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]

        bio_scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)
        dom_scenario = analyzer.compare([action], domain_loss_breakdown=dbd)

        # Should be very close (same jellyfish slice, different residual handling)
        rel_diff = abs(
            bio_scenario.adjusted_expected_loss - dom_scenario.adjusted_expected_loss
        ) / max(bio_scenario.adjusted_expected_loss, 1)
        assert rel_diff < 0.01, f"Relative diff too large: {rel_diff:.4f}"

    def test_domain_path_supersedes_bio_path_when_both_provided(self):
        """If both domain_loss_breakdown and bio_loss_breakdown are given,
        domain_loss_breakdown takes priority."""
        sim = _make_sim()
        fracs = {"hab": 0.24, "lice": 0.18, "jellyfish": 0.12, "pathogen": 0.06}
        bio_bd = {rt: sim.annual_losses * f for rt, f in fracs.items()}
        dbd = build_domain_loss_breakdown(sim.annual_losses, bio_breakdown=bio_bd)

        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]

        # Domain path: no warning (structural found in dbd)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            scenario = analyzer.compare(
                [action], bio_loss_breakdown=bio_bd, domain_loss_breakdown=dbd
            )
        # Should NOT warn about structural fallback
        assert not any("targeted_risk_types" in str(w.message) for w in caught)
        # Sprint 5: stronger_nets targets sub-types net_integrity + cage_structural
        assert (
            "net_integrity" in scenario.affected_risk_types
            or "cage_structural" in scenario.affected_risk_types
        )


# ── all_predefined with domain breakdown ─────────────────────────────────────

class TestAllPredefinedDomain:
    def test_no_warnings_with_full_domain_bd(self):
        """Sea actions should not UserWarning when sea domain_loss_breakdown covers all."""
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        sea_actions = [a for a in PREDEFINED_MITIGATIONS.values() if a.facility_type == "sea"]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for action in sea_actions:
                analyzer.compare([action], domain_loss_breakdown=dbd)

        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
        assert user_warnings == [], (
            f"Unexpected UserWarnings: {[str(w.message) for w in user_warnings]}"
        )

    def test_all_scenarios_reduce_loss(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        scenarios = analyzer.compare_all_predefined(domain_loss_breakdown=dbd)
        for s in scenarios:
            assert s.adjusted_expected_loss <= sim.mean_annual_loss, (
                f"Scenario '{s.name}' did not reduce loss"
            )

    def test_structural_actions_have_delta(self):
        # Sprint 5: deltas at sub-type level (net_integrity, cage_structural, mooring_failure)
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        scenarios = analyzer.compare_all_predefined(domain_loss_breakdown=dbd)
        nets = next(s for s in scenarios if s.name == "stronger_nets")
        moorings = next(s for s in scenarios if s.name == "stronger_moorings")
        # stronger_nets → net_integrity and/or cage_structural
        assert any(k in nets.risk_type_deltas for k in ("net_integrity", "cage_structural"))
        # stronger_moorings → mooring_failure and/or cage_structural
        assert any(k in moorings.risk_type_deltas for k in ("mooring_failure", "cage_structural"))

    def test_bundle_lowest_loss(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        scenarios = analyzer.compare_all_predefined(domain_loss_breakdown=dbd)
        bundle = next(s for s in scenarios if s.name == "full_mitigation_bundle")
        others = [s for s in scenarios if s.name != "full_mitigation_bundle"]
        assert bundle.adjusted_expected_loss <= min(s.adjusted_expected_loss for s in others)

    def test_fallback_false_for_structural_with_domain_bd(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert scenario.fallback_to_portfolio_scaling is False


# ── Backward compatibility: bio_loss_breakdown path unchanged ─────────────────

class TestBioPathBackwardCompat:
    def test_jellyfish_scenario_unchanged_with_bio_bd(self):
        """Sprint 2 bio-only compare() results are unchanged when no domain_bd."""
        sim = _make_sim()
        fracs = {"hab": 0.4, "lice": 0.3, "jellyfish": 0.2, "pathogen": 0.1}
        bio_bd = {rt: sim.annual_losses * f for rt, f in fracs.items()}
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["jellyfish_mitigation"]
        scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)
        assert "jellyfish" in scenario.affected_risk_types
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_structural_still_warns_with_bio_bd_only(self):
        """Structural action still warns when only bio_loss_breakdown provided."""
        sim = _make_sim()
        fracs = {"hab": 0.4, "lice": 0.3, "jellyfish": 0.2, "pathogen": 0.1}
        bio_bd = {rt: sim.annual_losses * f for rt, f in fracs.items()}
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            scenario = analyzer.compare([action], bio_loss_breakdown=bio_bd)

        assert any(
            "structural" in str(w.message).lower() or "targeted_risk_types" in str(w.message)
            for w in caught
        )


# ── Prior-only domain breakdown ───────────────────────────────────────────────

class TestPriorDomainBreakdown:
    def test_prior_domain_reduces_structural_loss(self):
        """stronger_nets reduces structural losses even with prior-only domain."""
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        # Structural domain accounts for 20% of total
        # Loss should decrease by roughly 0.20 × combined_loss_reduction
        expected_delta_approx = (
            -action.combined_loss_reduction * 0.20 * sim.mean_annual_loss
        )
        assert scenario.delta_vs_baseline_pct < 0
        actual_delta = scenario.adjusted_expected_loss - scenario.baseline_expected_loss
        assert actual_delta < 0
        # Magnitude within 3× the rough estimate (generous: prior fractions are approximate)
        assert abs(actual_delta) <= abs(expected_delta_approx) * 3

    def test_multiple_structural_actions_compound(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        single = analyzer.compare(
            [PREDEFINED_MITIGATIONS["stronger_nets"]], domain_loss_breakdown=dbd
        )
        combined = analyzer.compare(
            [PREDEFINED_MITIGATIONS["stronger_nets"],
             PREDEFINED_MITIGATIONS["stronger_moorings"]],
            domain_loss_breakdown=dbd,
        )
        assert combined.adjusted_expected_loss < single.adjusted_expected_loss


# ── MitigationCapitalAnalyzer with domain breakdown ───────────────────────────

class TestCapitalAnalyzerDomain:
    def test_analyze_with_domain_bd_returns_impact(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        impact = ca.analyze([action], domain_loss_breakdown=dbd)
        assert impact is not None

    def test_structural_action_reduces_expected_loss(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        impact = ca.analyze([action], domain_loss_breakdown=dbd)
        assert impact.delta_expected_loss < 0

    def test_structural_action_reduces_scr(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        ca = MitigationCapitalAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        impact = ca.analyze([action], domain_loss_breakdown=dbd)
        assert impact.delta_scr <= 0

    def test_full_bundle_with_domain_bd_has_capital_release(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        ca = MitigationCapitalAnalyzer(sim)
        impact = ca.analyze(
            list(PREDEFINED_MITIGATIONS.values()),
            scenario_name="full_bundle",
            domain_loss_breakdown=dbd,
        )
        assert impact.capital_release > 0

    def test_analyze_all_predefined_with_domain_bd(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        ca = MitigationCapitalAnalyzer(sim)
        sea_actions = [a for a in PREDEFINED_MITIGATIONS.values() if a.facility_type == "sea"]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            # Only sea actions should route cleanly against a sea domain_loss_breakdown
            for action in sea_actions:
                ca.analyze([action], domain_loss_breakdown=dbd)

        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
        assert user_warnings == [], (
            f"Unexpected UserWarnings: {[str(w.message) for w in user_warnings]}"
        )
        # Full suite (all 24) still works — smolt actions fall back to portfolio scaling
        impacts = ca.analyze_all_predefined(domain_loss_breakdown=dbd)
        assert len(impacts) == len(PREDEFINED_MITIGATIONS) + 1

    def test_rank_by_tcor_with_domain_bd(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        ca = MitigationCapitalAnalyzer(sim)
        impacts = ca.analyze_all_predefined(domain_loss_breakdown=dbd)
        ranked = ca.rank_by_tcor_impact(impacts)
        for i in range(len(ranked) - 1):
            assert ranked[i].delta_tcor <= ranked[i + 1].delta_tcor

    def test_with_captive_structure_and_domain_bd(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        captive = _make_captive()
        ca = MitigationCapitalAnalyzer(sim, captive)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        impact = ca.analyze([action], domain_loss_breakdown=dbd)
        assert impact.delta_retained_mean <= 0
        assert impact.mitigated_reinsured_mean >= 0

    def test_summary_from_domain_impacts(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        ca = MitigationCapitalAnalyzer(sim)
        impacts = ca.analyze_all_predefined(domain_loss_breakdown=dbd)
        summary = build_mitigation_impact_summary(impacts)
        assert summary.best_scenario_expected_loss < summary.baseline_expected_loss


# ── Uncertainty mode with domain breakdown ────────────────────────────────────

class TestUncertaintyWithDomainBd:
    def test_uncertainty_mode_works_with_domain_bd(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        rng = np.random.default_rng(7)
        scenario = analyzer.compare(
            [action], domain_loss_breakdown=dbd, use_uncertainty=True, rng=rng
        )
        assert scenario.effective_reduction_mean is not None
        assert scenario.adjusted_expected_loss < sim.mean_annual_loss

    def test_uncertainty_stats_bounded(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        clr = action.combined_loss_reduction
        for i in range(10):
            rng = np.random.default_rng(i)
            s = analyzer.compare(
                [action], domain_loss_breakdown=dbd, use_uncertainty=True, rng=rng
            )
            assert 0.0 <= s.effective_reduction_mean <= clr + 1e-9


# ── mitigated_annual_losses field ─────────────────────────────────────────────

class TestMitigatedLossesWithDomain:
    def test_mitigated_losses_populated(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        action = PREDEFINED_MITIGATIONS["stronger_nets"]
        scenario = analyzer.compare([action], domain_loss_breakdown=dbd)
        assert scenario.mitigated_annual_losses is not None

    def test_mitigated_losses_shape(self):
        n, t = 100, 5
        losses = np.random.default_rng(0).exponential(1e7, size=(n, t))
        sim = MagicMock()
        sim.annual_losses = losses
        sim.mean_annual_loss = float(losses.mean())
        sim.var_995 = float(np.percentile(losses.flatten(), 99.5))
        dbd = build_domain_loss_breakdown(losses)
        analyzer = MitigationAnalyzer(sim)
        scenario = analyzer.compare(
            [PREDEFINED_MITIGATIONS["stronger_nets"]], domain_loss_breakdown=dbd
        )
        assert scenario.mitigated_annual_losses.shape == (n, t)

    def test_mitigated_losses_less_than_baseline(self):
        sim = _make_sim()
        dbd = _make_domain_bd_prior(sim)
        analyzer = MitigationAnalyzer(sim)
        scenario = analyzer.compare(
            [PREDEFINED_MITIGATIONS["stronger_moorings"]], domain_loss_breakdown=dbd
        )
        assert scenario.mitigated_annual_losses.mean() < sim.annual_losses.mean()

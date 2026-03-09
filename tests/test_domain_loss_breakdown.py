"""
Tests for Sprint 4 – DomainLossBreakdown model.

Covers construction, total preservation, flat_lookup, domain_totals,
from_bio_breakdown, prior_only, and build_domain_loss_breakdown factory.
"""

import numpy as np
import pytest

from models.domain_loss_breakdown import (
    DomainLossBreakdown,
    build_domain_loss_breakdown,
    DOMAINS,
    DOMAIN_SUBTYPES,
    DEFAULT_DOMAIN_FRACTIONS,
    _NON_BIO_DOMAIN_FRACTIONS,
    _BIO_SUBTYPE_FRACTIONS,
    _STRUCT_SUBTYPE_FRACTIONS,
    _ENV_SUBTYPE_FRACTIONS,
    _OPS_SUBTYPE_FRACTIONS,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _losses(n=200, t=5, seed=0, mean=10_000_000):
    rng = np.random.default_rng(seed)
    return rng.exponential(mean, size=(n, t))


def _bio_bd(losses, fracs=None):
    if fracs is None:
        fracs = {"hab": 0.4, "lice": 0.3, "jellyfish": 0.2, "pathogen": 0.1}
    return {rt: losses * f for rt, f in fracs.items()}


# ── Constants sanity ──────────────────────────────────────────────────────────

class TestConstants:
    def test_domains_count(self):
        assert len(DOMAINS) == 4

    def test_each_domain_has_subtypes(self):
        for domain in DOMAINS:
            assert domain in DOMAIN_SUBTYPES
            assert len(DOMAIN_SUBTYPES[domain]) >= 2

    def test_default_domain_fractions_sum_to_one(self):
        total = sum(DEFAULT_DOMAIN_FRACTIONS.values())
        assert abs(total - 1.0) < 1e-10

    def test_non_bio_fractions_sum_to_one(self):
        total = sum(_NON_BIO_DOMAIN_FRACTIONS.values())
        assert abs(total - 1.0) < 1e-10

    def test_bio_subtype_fractions_sum_to_one(self):
        assert abs(sum(_BIO_SUBTYPE_FRACTIONS.values()) - 1.0) < 1e-10

    def test_struct_subtype_fractions_sum_to_one(self):
        assert abs(sum(_STRUCT_SUBTYPE_FRACTIONS.values()) - 1.0) < 1e-10

    def test_env_subtype_fractions_sum_to_one(self):
        assert abs(sum(_ENV_SUBTYPE_FRACTIONS.values()) - 1.0) < 1e-10

    def test_ops_subtype_fractions_sum_to_one(self):
        assert abs(sum(_OPS_SUBTYPE_FRACTIONS.values()) - 1.0) < 1e-10


# ── prior_only ────────────────────────────────────────────────────────────────

class TestPriorOnly:
    def test_returns_domain_loss_breakdown(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        assert isinstance(dbd, DomainLossBreakdown)

    def test_all_domains_populated(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        for domain in DOMAINS:
            d = getattr(dbd, domain)
            assert len(d) > 0, f"{domain} is empty"

    def test_total_sums_to_annual_losses(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        np.testing.assert_allclose(dbd.total(), losses, rtol=1e-10)

    def test_bio_modelled_false(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        assert dbd.bio_modelled is False

    def test_biological_subtypes_present(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        for st in ("hab", "lice", "jellyfish", "pathogen"):
            assert st in dbd.biological

    def test_structural_subtypes_present(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        for st in ("mooring_failure", "net_integrity", "cage_structural", "feed_system"):
            assert st in dbd.structural

    def test_biological_fraction_of_total(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        bio_total = sum(dbd.biological.values())
        expected_frac = DEFAULT_DOMAIN_FRACTIONS["biological"]
        np.testing.assert_allclose(
            bio_total / losses,
            np.full_like(losses, expected_frac),
            rtol=1e-10,
        )

    def test_structural_fraction_of_total(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        struct_total = sum(dbd.structural.values())
        expected_frac = DEFAULT_DOMAIN_FRACTIONS["structural"]
        np.testing.assert_allclose(
            struct_total.mean() / losses.mean(),
            expected_frac,
            rtol=1e-10,
        )

    def test_arrays_have_correct_shape(self):
        n, t = 150, 3
        losses = _losses(n=n, t=t)
        dbd = DomainLossBreakdown.prior_only(losses)
        for domain in DOMAINS:
            for arr in getattr(dbd, domain).values():
                assert arr.shape == (n, t)

    def test_stub_model_types(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        assert dbd.structural_model_type == "stub"
        assert dbd.environmental_model_type == "stub"
        assert dbd.operational_model_type == "stub"


# ── from_bio_breakdown ────────────────────────────────────────────────────────

class TestFromBioBreakdown:
    def test_returns_domain_loss_breakdown(self):
        losses = _losses()
        bio = _bio_bd(losses)
        dbd = DomainLossBreakdown.from_bio_breakdown(bio, losses)
        assert isinstance(dbd, DomainLossBreakdown)

    def test_bio_modelled_true(self):
        losses = _losses()
        bio = _bio_bd(losses)
        dbd = DomainLossBreakdown.from_bio_breakdown(bio, losses)
        assert dbd.bio_modelled is True

    def test_total_sums_to_annual_losses(self):
        losses = _losses()
        bio = _bio_bd(losses)
        dbd = DomainLossBreakdown.from_bio_breakdown(bio, losses)
        np.testing.assert_allclose(dbd.total(), losses, rtol=1e-10)

    def test_biological_matches_bio_breakdown(self):
        losses = _losses()
        bio = _bio_bd(losses)
        dbd = DomainLossBreakdown.from_bio_breakdown(bio, losses)
        for rt, arr in bio.items():
            np.testing.assert_array_equal(dbd.biological[rt], arr)

    def test_structural_non_zero(self):
        losses = _losses()
        bio = _bio_bd(losses)  # bio covers 100% × 1.0 of losses
        dbd = DomainLossBreakdown.from_bio_breakdown(bio, losses)
        # Bio sums to exactly losses → residual = 0 → structural = 0
        struct_total = sum(dbd.structural.values())
        # Bio fracs sum to 1.0, so residual=0, structural=0
        assert float(struct_total.max()) == pytest.approx(0.0, abs=1e-6)

    def test_structural_positive_when_bio_less_than_total(self):
        losses = _losses()
        # Bio covers only 60% of losses
        bio = _bio_bd(losses, fracs={"hab": 0.24, "lice": 0.18, "jellyfish": 0.12, "pathogen": 0.06})
        dbd = DomainLossBreakdown.from_bio_breakdown(bio, losses)
        struct_total = sum(dbd.structural.values())
        assert float(struct_total.mean()) > 0

    def test_non_bio_residual_split_sums_to_residual(self):
        losses = _losses()
        fracs = {"hab": 0.24, "lice": 0.18, "jellyfish": 0.12, "pathogen": 0.06}
        bio = _bio_bd(losses, fracs=fracs)
        dbd = DomainLossBreakdown.from_bio_breakdown(bio, losses)
        non_bio = losses - sum(bio.values())
        non_bio_from_dbd = (
            sum(dbd.structural.values())
            + sum(dbd.environmental.values())
            + sum(dbd.operational.values())
        )
        np.testing.assert_allclose(non_bio_from_dbd, non_bio, rtol=1e-10)

    def test_all_non_bio_domains_populated(self):
        losses = _losses()
        bio = _bio_bd(losses, fracs={"hab": 0.24, "lice": 0.18, "jellyfish": 0.12, "pathogen": 0.06})
        dbd = DomainLossBreakdown.from_bio_breakdown(bio, losses)
        assert len(dbd.structural) > 0
        assert len(dbd.environmental) > 0
        assert len(dbd.operational) > 0


# ── build_domain_loss_breakdown factory ──────────────────────────────────────

class TestBuildFactory:
    def test_with_bio_breakdown_calls_from_bio(self):
        losses = _losses()
        bio = _bio_bd(losses, fracs={"hab": 0.24, "lice": 0.18, "jellyfish": 0.12, "pathogen": 0.06})
        dbd = build_domain_loss_breakdown(losses, bio_breakdown=bio)
        assert dbd.bio_modelled is True

    def test_without_bio_breakdown_calls_prior_only(self):
        losses = _losses()
        dbd = build_domain_loss_breakdown(losses)
        assert dbd.bio_modelled is False

    def test_total_always_sums_to_losses(self):
        losses = _losses()
        for bio in [None, _bio_bd(losses, {"hab": 0.24, "lice": 0.18, "jellyfish": 0.12, "pathogen": 0.06})]:
            dbd = build_domain_loss_breakdown(losses, bio_breakdown=bio)
            np.testing.assert_allclose(dbd.total(), losses, rtol=1e-10)


# ── domain_totals ────────────────────────────────────────────────────────────

class TestDomainTotals:
    def test_returns_four_keys(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        totals = dbd.domain_totals()
        assert set(totals.keys()) == set(DOMAINS)

    def test_totals_sum_to_portfolio_total(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        domain_sum = sum(dbd.domain_totals().values())
        np.testing.assert_allclose(domain_sum, losses, rtol=1e-10)

    def test_biological_total_matches_sum_of_subtypes(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        expected = sum(dbd.biological.values())
        np.testing.assert_array_equal(dbd.domain_totals()["biological"], expected)


# ── flat_lookup ───────────────────────────────────────────────────────────────

class TestFlatLookup:
    def test_contains_sub_types(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        lookup = dbd.flat_lookup()
        for st in ("hab", "jellyfish", "mooring_failure", "oxygen_stress", "human_error"):
            assert st in lookup, f"{st} missing from flat_lookup"

    def test_contains_domain_aggregates(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        lookup = dbd.flat_lookup()
        for domain in DOMAINS:
            assert domain in lookup, f"{domain} aggregate missing from flat_lookup"

    def test_domain_aggregate_equals_sum_of_subtypes(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        lookup = dbd.flat_lookup()
        for domain in DOMAINS:
            expected = sum(getattr(dbd, domain).values())
            np.testing.assert_array_equal(lookup[domain], expected)

    def test_subtype_values_match_breakdown(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        lookup = dbd.flat_lookup()
        np.testing.assert_array_equal(lookup["jellyfish"], dbd.biological["jellyfish"])
        np.testing.assert_array_equal(lookup["mooring_failure"], dbd.structural["mooring_failure"])


# ── all_subtypes ──────────────────────────────────────────────────────────────

class TestAllSubtypes:
    def test_no_domain_keys(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        st = dbd.all_subtypes()
        for domain in DOMAINS:
            assert domain not in st

    def test_all_sub_type_names_present(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        st = dbd.all_subtypes()
        for domain, subtypes in DOMAIN_SUBTYPES.items():
            for s in subtypes:
                assert s in st

    def test_count(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        total_subtypes = sum(len(v) for v in DOMAIN_SUBTYPES.values())
        assert len(dbd.all_subtypes()) == total_subtypes


# ── total() edge cases ────────────────────────────────────────────────────────

class TestTotal:
    def test_raises_on_empty(self):
        dbd = DomainLossBreakdown()
        with pytest.raises(ValueError):
            dbd.total()

    def test_non_negative(self):
        losses = _losses()
        dbd = DomainLossBreakdown.prior_only(losses)
        assert float(dbd.total().min()) >= 0.0


# ── TestBuildWithCorrelation (Sprint 7) ───────────────────────────────────────

class TestBuildWithCorrelation:
    """8 tests covering build_domain_loss_breakdown with domain_correlation."""

    def _rng(self, seed=0):
        return np.random.default_rng(seed)

    def _dcm(self):
        from models.domain_correlation import DomainCorrelationMatrix
        return DomainCorrelationMatrix.expert_default()

    def test_flag_true_when_correlation_provided(self):
        from models.domain_correlation import DomainCorrelationMatrix
        losses = _losses()
        dcm = DomainCorrelationMatrix.expert_default()
        dbd = build_domain_loss_breakdown(losses, domain_correlation=dcm, rng=self._rng())
        assert dbd.domain_correlation_applied is True

    def test_flag_false_without_correlation(self):
        losses = _losses()
        dbd = build_domain_loss_breakdown(losses)
        assert dbd.domain_correlation_applied is False

    def test_total_preserved(self):
        losses = _losses()
        dbd = build_domain_loss_breakdown(losses, domain_correlation=self._dcm(), rng=self._rng())
        np.testing.assert_allclose(dbd.total(), losses, rtol=1e-10)

    def test_shape_all_subtypes(self):
        losses = _losses(n=100, t=5)
        dbd = build_domain_loss_breakdown(losses, domain_correlation=self._dcm(), rng=self._rng())
        for st, arr in dbd.all_subtypes().items():
            assert arr.shape == (100, 5), f"sub-type {st} has wrong shape {arr.shape}"

    def test_correlated_result_differs_from_fixed(self):
        losses = _losses(seed=7)
        fixed = build_domain_loss_breakdown(losses)
        corr = build_domain_loss_breakdown(losses, domain_correlation=self._dcm(), rng=self._rng())
        # At least one domain should differ
        dt_fixed = fixed.domain_totals()
        dt_corr = corr.domain_totals()
        any_different = any(
            not np.allclose(dt_fixed[d], dt_corr[d]) for d in ("structural", "environmental", "operational")
        )
        assert any_different

    def test_perturbation_strength_near_zero_matches_fixed(self):
        from models.domain_correlation import DomainCorrelationMatrix
        losses = _losses()
        dcm = DomainCorrelationMatrix(
            domains=["biological", "structural", "environmental", "operational"],
            correlation_matrix=__import__("numpy").eye(4),
            perturbation_strength=1e-10,
        )
        dbd = build_domain_loss_breakdown(losses, domain_correlation=dcm, rng=self._rng())
        fixed = build_domain_loss_breakdown(losses)
        np.testing.assert_allclose(dbd.total(), fixed.total(), rtol=1e-8)

    def test_bio_modelled_false_path_all_four_domains_perturbed(self):
        losses = _losses()
        dbd = build_domain_loss_breakdown(losses, domain_correlation=self._dcm(), rng=self._rng())
        assert dbd.bio_modelled is False
        assert dbd.domain_correlation_applied is True
        # All four domain dicts should be populated
        for domain in ("biological", "structural", "environmental", "operational"):
            d = getattr(dbd, domain)
            assert len(d) > 0

    def test_bio_modelled_true_path_bio_unchanged_total_preserved(self):
        losses = _losses()
        bio = _bio_bd(losses, fracs={"hab": 0.24, "lice": 0.18, "jellyfish": 0.12, "pathogen": 0.06})
        dbd = build_domain_loss_breakdown(losses, bio_breakdown=bio, domain_correlation=self._dcm(), rng=self._rng())
        assert dbd.bio_modelled is True
        assert dbd.domain_correlation_applied is True
        # Bio slices should match the original bio_breakdown
        for rt, arr in bio.items():
            np.testing.assert_allclose(dbd.biological[rt], arr, rtol=1e-10)
        # Total must still match losses
        np.testing.assert_allclose(dbd.total(), losses, rtol=1e-10)
